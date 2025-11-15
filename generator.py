import json
from pathlib import Path
from typing import Dict
from analyzer import SiteAnalyzer
from llm_client import LLMClient
from template import generate_scraper_code
from validator import ScraperValidator


class ScraperGenerator:
    """Головний клас для генерації скрейперів"""

    def __init__(self, output_dir: str = "scrapers"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.llm_client = LLMClient()
        self.validator = ScraperValidator()

    def generate(self, site_url: str, max_retries: int = 2) -> Dict:
        """Генерує скрейпер для вказаного сайту"""
        print(f"\n{'='*60}")
        print(f"Generating scraper for: {site_url}")
        print(f"{'='*60}\n")

        print("Step 1: Analyzing site structure...")
        analyzer = SiteAnalyzer(site_url)
        analysis = analyzer.analyze()

        if not analysis['homepage_html']:
            return {'success': False, 'error': 'Failed to fetch homepage'}

        if len(analysis['article_samples']) == 0:
            return {'success': False, 'error': 'No article samples found'}

        print(f"Found {analysis['num_samples']} article samples")

        print("\nStep 2: Generating CSS selectors with LLM...")
        selectors = self.llm_client.analyze_site_structure(
            site_url=site_url,
            homepage_html=analysis['homepage_html'],
            article_samples=analysis['article_samples']
        )

        print(f"Generated selectors:")
        print(json.dumps(selectors, indent=2, ensure_ascii=False))

        print("\nStep 3: Validating selectors...")
        validation = self.validator.validate_selectors(
            selectors=selectors,
            homepage_html=analysis['homepage_html'],
            article_samples=analysis['article_samples']
        )

        print(f"Validation score: {validation['overall_score']:.2%}")

        retry_count = 0
        while not self.validator.is_valid(validation) and retry_count < max_retries:
            print(f"\nStep 4: Refining selectors (attempt {retry_count + 1}/{max_retries})...")

            selectors = self.llm_client.refine_selectors(
                site_url=site_url,
                current_selectors=selectors,
                validation_results=validation
            )

            validation = self.validator.validate_selectors(
                selectors=selectors,
                homepage_html=analysis['homepage_html'],
                article_samples=analysis['article_samples']
            )

            print(f"New validation score: {validation['overall_score']:.2%}")
            retry_count += 1

        print("\nStep 5: Generating scraper code...")
        scraper_code = generate_scraper_code(site_url, selectors)

        filename = self._get_filename(site_url)
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(scraper_code)

        print(f"\nScraper saved to: {filepath}")

        metadata = {
            'site_url': site_url,
            'selectors': selectors,
            'validation': validation,
            'filename': filename
        }

        metadata_file = self.output_dir / f"{filename.replace('.py', '_metadata.json')}"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"Metadata saved to: {metadata_file}")

        print(f"\n{'='*60}")
        print(f"✓ Scraper generation completed!")
        print(f"  Validation score: {validation['overall_score']:.2%}")
        print(f"  Output file: {filepath}")
        print(f"{'='*60}\n")

        return {
            'success': True,
            'filepath': str(filepath),
            'metadata_file': str(metadata_file),
            'validation_score': validation['overall_score'],
            'selectors': selectors
        }

    def _get_filename(self, site_url: str) -> str:
        """Генерує ім'я файлу з URL"""
        domain = site_url.replace('https://', '').replace('http://', '').replace('www.', '')
        domain = domain.split('/')[0].replace('.', '_').replace('-', '_')
        return f"{domain}_scraper.py"

    def generate_batch(self, site_urls: list) -> Dict:
        """Генерує скрейпери для списку сайтів"""
        results = {}

        for i, url in enumerate(site_urls, 1):
            print(f"\nProcessing site {i}/{len(site_urls)}")
            try:
                result = self.generate(url)
                results[url] = result
            except Exception as e:
                print(f"Error generating scraper for {url}: {e}")
                results[url] = {'success': False, 'error': str(e)}

        report_file = self.output_dir / "generation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"Batch generation completed!")
        print(f"Report saved to: {report_file}")
        print(f"{'='*60}\n")

        successful = sum(1 for r in results.values() if r.get('success', False))
        print(f"Success rate: {successful}/{len(site_urls)}")

        return results
