import os
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
        """
        Ініціалізація генератора

        Args:
            output_dir: Директорія для збереження згенерованих скрейперів
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.llm_client = LLMClient()
        self.validator = ScraperValidator()

    def generate(self, site_url: str, max_retries: int = 2) -> Dict:
        """
        Генерує скрейпер для вказаного сайту

        Args:
            site_url: URL сайту
            max_retries: Максимальна кількість спроб уточнення

        Returns:
            Словник з інформацією про згенерований скрейпер
        """
        print(f"\n{'='*60}")
        print(f"Generating scraper for: {site_url}")
        print(f"{'='*60}\n")

        # Крок 1: Аналіз сайту
        print("Step 1: Analyzing site structure...")
        analyzer = SiteAnalyzer(site_url)
        analysis = analyzer.analyze()

        if not analysis['homepage_html']:
            return {
                'success': False,
                'error': 'Failed to fetch homepage'
            }

        if len(analysis['article_samples']) == 0:
            # Проверяем, возможно ли это SPA (Single Page Application)
            is_spa = self._detect_spa(analysis['homepage_html'])

            if is_spa:
                error_msg = (
                    "⚠️  This website appears to use JavaScript rendering (SPA/React/Vue/Angular).\n\n"
                    "The scraper generator currently works with server-rendered HTML sites only.\n"
                    "JavaScript-based sites require browser automation (Selenium/Playwright), which is not yet supported.\n\n"
                    "Detected framework indicators:\n" + "\n".join(f"  - {indicator}" for indicator in is_spa)
                )
            else:
                error_msg = (
                    "❌ No article/blog posts found on this website.\n\n"
                    "Possible reasons:\n"
                    "  - The site doesn't have a blog or articles section\n"
                    "  - Articles are behind authentication/paywall\n"
                    "  - The site structure is non-standard\n\n"
                    "Try providing a direct URL to the blog page (e.g., https://example.com/blog/)"
                )

            print(f"\n{error_msg}\n")
            return {
                'success': False,
                'error': error_msg
            }

        print(f"Found {analysis['num_samples']} article samples")

        # Крок 2: Генерація селекторів через LLM
        print("\nStep 2: Generating CSS selectors with LLM...")

        selectors = self.llm_client.analyze_site_structure(
            site_url=site_url,
            homepage_html=analysis['homepage_html'],
            article_samples=analysis['article_samples'],
            article_urls=analysis.get('article_urls', [])  # Передаємо список URLs для кращого аналізу
        )

        # Post-process selectors
        selectors = self._postprocess_selectors(selectors, analysis)

        print(f"Generated selectors:")
        print(json.dumps(selectors, indent=2, ensure_ascii=False))

        # Крок 3: Валідація селекторів
        print("\nStep 3: Validating selectors...")

        # Використовуємо blog_page_html для валідації article_links якщо доступно
        validation_html = analysis.get('blog_page_html') or analysis['homepage_html']

        validation = self.validator.validate_selectors(
            selectors=selectors,
            homepage_html=validation_html,
            article_samples=analysis['article_samples']
        )

        print(f"Validation score: {validation['overall_score']:.2%}")

        # Крок 4: Уточнення якщо потрібно
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
                homepage_html=validation_html,
                article_samples=analysis['article_samples']
            )

            print(f"New validation score: {validation['overall_score']:.2%}")
            retry_count += 1

        # Крок 5: Генерація коду
        print("\nStep 5: Generating scraper code...")

        # Додаємо blog_page_path для правильної пагінації
        blog_page_url = analysis.get('blog_page_url')
        if blog_page_url:
            from urllib.parse import urlparse
            blog_page_path = urlparse(blog_page_url).path
            selectors['blog_page_path'] = blog_page_path
        else:
            # Якщо немає окремої blog page, pagination від homepage (корня)
            selectors['blog_page_path'] = '/'

        scraper_code = generate_scraper_code(site_url, selectors)

        # Крок 6: Збереження
        filename = self._get_filename(site_url)
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(scraper_code)

        print(f"\nScraper saved to: {filepath}")

        # Збереження метаданих
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

    def _postprocess_selectors(self, selectors: Dict, analysis: Dict) -> Dict:
        """
        Post-processes selectors to fix common issues

        Args:
            selectors: Generated selectors
            analysis: Site analysis data

        Returns:
            Processed selectors
        """
        import re
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        # Fix base_url_pattern - convert regex to simple path
        base_url_pattern = selectors.get('base_url_pattern', '')

        # Always analyze actual article URLs for the path pattern
        article_samples = analysis.get('article_samples', [])
        if article_samples:
            first_url = article_samples[0].get('url', '')
            path = urlparse(first_url).path
            parts = [p for p in path.split('/') if p]
            if parts:
                selectors['article_path_pattern'] = f'/{parts[0]}/'
            else:
                selectors['article_path_pattern'] = '/blog/'
        else:
            # Fallback: try to extract from regex pattern
            if base_url_pattern:
                # Extract path from regex like ^/reviews/[\w-]+/$ or ^https?://localhost:8888/reviews/[\w-]+/?$
                # Look for /word/ pattern after domain or at start
                match = re.search(r'(?:^|8888)/([a-z-]+)/', base_url_pattern)
                if match:
                    article_path_pattern = f'/{match.group(1)}/'
                    selectors['article_path_pattern'] = article_path_pattern
                else:
                    selectors['article_path_pattern'] = '/blog/'
            else:
                selectors['article_path_pattern'] = '/blog/'

        # Fix selectors to work on article pages, not listing pages
        # Check if title_selector and content_selector work on article pages
        article_samples = analysis.get('article_samples', [])
        if article_samples:
            # Test current selectors on first article
            sample_html = article_samples[0].get('html', '')
            if sample_html:
                soup = BeautifulSoup(sample_html, 'html.parser')

                # Fix title selector if needed
                title_elem = soup.select_one(selectors.get('title_selector', ''))
                if not title_elem:
                    # Try common article title selectors
                    for selector in ['article h1', '.article-title', '.post-title', 'h1']:
                        elem = soup.select_one(selector)
                        if elem:
                            selectors['title_selector'] = selector
                            break

                # Fix content selector if needed
                content_elem = soup.select_one(selectors.get('content_selector', ''))
                if not content_elem:
                    # Try common article content selectors
                    for selector in ['article .content', 'article .review-content', '.article-body', '.post-content', 'article']:
                        elem = soup.select_one(selector)
                        if elem:
                            selectors['content_selector'] = selector
                            break

        return selectors

    def _detect_spa(self, html: str) -> list:
        """
        Определяет признаки JavaScript-рендеринга (SPA frameworks)

        Args:
            html: HTML страницы

        Returns:
            Список обнаруженных индикаторов или пустой список, если это не SPA
        """
        indicators = []
        html_lower = html.lower()

        # React
        if 'react' in html_lower or 'reactdom' in html_lower or '__react' in html_lower:
            indicators.append("React framework detected")

        # Vue.js
        if 'vue.js' in html_lower or 'vue.min.js' in html_lower or 'v-if=' in html or 'v-for=' in html:
            indicators.append("Vue.js framework detected")

        # Angular
        if 'angular' in html_lower or 'ng-app' in html_lower or 'ng-controller' in html_lower:
            indicators.append("Angular framework detected")

        # Next.js
        if '__next' in html_lower or 'next/static' in html_lower or '_next/static' in html_lower:
            indicators.append("Next.js framework detected")

        # Nuxt.js
        if '__nuxt' in html_lower or 'nuxt.js' in html_lower:
            indicators.append("Nuxt.js framework detected")

        # Generic SPA indicators
        if '<div id="root"></div>' in html or '<div id="app"></div>' in html:
            indicators.append("Empty root div (typical for SPAs)")

        # Check for heavy JavaScript frameworks and loaders
        if 'webpack' in html_lower or '__webpack' in html_lower:
            indicators.append("Webpack module loader detected")

        if 'newrelic' in html_lower or 'nr-data.net' in html_lower:
            indicators.append("New Relic monitoring (common in SPAs)")

        # Very small body with mostly scripts
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        body = soup.find('body')
        if body:
            # Count text vs script content
            scripts = body.find_all('script')
            total_script_length = sum(len(str(script)) for script in scripts)
            body_text = body.get_text(strip=True)

            # If body is mostly scripts and very little meaningful text
            if total_script_length > 5000 and len(body_text) < 500:
                indicators.append("Minimal HTML content (body mostly contains scripts)")
            # Or if scripts dominate even with more text
            elif total_script_length > 15000 and total_script_length / max(1, len(body_text)) > 1.2:
                indicators.append("Heavy JavaScript content (script/text ratio too high)")

        return indicators

    def _get_filename(self, site_url: str) -> str:
        """
        Генерує ім'я файлу з URL

        Args:
            site_url: URL сайту

        Returns:
            Ім'я файлу для скрейпера
        """
        domain = site_url.replace('https://', '').replace('http://', '').replace('www.', '')
        domain = domain.split('/')[0]

        # Обробка localhost - використовуємо "local_site" замість "localhost:port"
        if domain.startswith('localhost'):
            domain = 'local_site'
        else:
            # Заміна недопустимих символів для звичайних доменів
            domain = domain.replace('.', '_').replace('-', '_').replace(':', '_')

        return f"{domain}_scraper.py"

    def generate_batch(self, site_urls: list) -> Dict:
        """
        Генерує скрейпери для списку сайтів

        Args:
            site_urls: Список URL сайтів

        Returns:
            Словник з результатами для кожного сайту
        """
        results = {}

        for i, url in enumerate(site_urls, 1):
            print(f"\nProcessing site {i}/{len(site_urls)}")
            try:
                result = self.generate(url)
                results[url] = result
            except Exception as e:
                print(f"Error generating scraper for {url}: {e}")
                results[url] = {
                    'success': False,
                    'error': str(e)
                }

        # Збереження загального звіту
        report_file = self.output_dir / "generation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"Batch generation completed!")
        print(f"Report saved to: {report_file}")
        print(f"{'='*60}\n")

        # Статистика
        successful = sum(1 for r in results.values() if r.get('success', False))
        print(f"Success rate: {successful}/{len(site_urls)}")

        return results


if __name__ == "__main__":
    # Приклад використання
    generator = ScraperGenerator(output_dir="scrapers")

    # Для URL
    # result = generator.generate("https://anadea.info/")
