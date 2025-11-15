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

    def generate(self, site_url: str, max_retries: int = 2, is_local: bool = False) -> Dict:
        """
        Генерує скрейпер для вказаного сайту

        Args:
            site_url: URL сайту або шлях до локальної директорії
            max_retries: Максимальна кількість спроб уточнення
            is_local: True якщо це локальна директорія з HTML файлами

        Returns:
            Словник з інформацією про згенерований скрейпер
        """
        print(f"\n{'='*60}")
        if is_local:
            print(f"Generating scraper for LOCAL site: {site_url}")
        else:
            print(f"Generating scraper for: {site_url}")
        print(f"{'='*60}\n")

        # Крок 1: Аналіз сайту
        print("Step 1: Analyzing site structure...")
        analyzer = SiteAnalyzer(site_url, is_local=is_local)
        analysis = analyzer.analyze()

        if not analysis['homepage_html']:
            return {
                'success': False,
                'error': 'Failed to fetch homepage'
            }

        if len(analysis['article_samples']) == 0:
            return {
                'success': False,
                'error': 'No article samples found'
            }

        print(f"Found {analysis['num_samples']} article samples")

        # Крок 2: Генерація селекторів через LLM
        print("\nStep 2: Generating CSS selectors with LLM...")

        # Для LLM використовуємо реальний URL або псевдо-URL для локальних файлів
        llm_url = site_url if not is_local else f"file://{Path(site_url).absolute()}"

        selectors = self.llm_client.analyze_site_structure(
            site_url=llm_url,
            homepage_html=analysis['homepage_html'],
            article_samples=analysis['article_samples']
        )

        print(f"Generated selectors:")
        print(json.dumps(selectors, indent=2, ensure_ascii=False))

        # Крок 3: Валідація селекторів
        print("\nStep 3: Validating selectors...")
        validation = self.validator.validate_selectors(
            selectors=selectors,
            homepage_html=analysis['homepage_html'],
            article_samples=analysis['article_samples']
        )

        print(f"Validation score: {validation['overall_score']:.2%}")

        # Крок 4: Уточнення якщо потрібно
        retry_count = 0
        while not self.validator.is_valid(validation) and retry_count < max_retries:
            print(f"\nStep 4: Refining selectors (attempt {retry_count + 1}/{max_retries})...")

            selectors = self.llm_client.refine_selectors(
                site_url=llm_url,
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

        # Крок 5: Генерація коду
        print("\nStep 5: Generating scraper code...")

        if is_local:
            scraper_code = self._generate_local_scraper_code(site_url, selectors)
        else:
            scraper_code = generate_scraper_code(site_url, selectors)

        # Крок 6: Збереження
        filename = self._get_filename(site_url, is_local)
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(scraper_code)

        print(f"\nScraper saved to: {filepath}")

        # Збереження метаданих
        metadata = {
            'site_url': site_url,
            'is_local': is_local,
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

    def _get_filename(self, site_url: str, is_local: bool) -> str:
        """
        Генерує ім'я файлу з URL або шляху

        Args:
            site_url: URL сайту або шлях до директорії
            is_local: Чи це локальний сайт

        Returns:
            Ім'я файлу для скрейпера
        """
        if is_local:
            # Для локальних файлів використовуємо назву директорії
            name = Path(site_url).name
            name = name.replace('-', '_').replace(' ', '_')
            return f"{name}_local_scraper.py"
        else:
            # Для URL використовуємо домен
            domain = site_url.replace('https://', '').replace('http://', '').replace('www.', '')
            domain = domain.split('/')[0].replace('.', '_').replace('-', '_')
            return f"{domain}_scraper.py"

    def _generate_local_scraper_code(self, site_dir: str, selectors: Dict) -> str:
        """
        Генерує код скрейпера для локальних файлів

        Args:
            site_dir: Шлях до директорії з HTML файлами
            selectors: CSS селектори

        Returns:
            Згенерований Python код
        """
        site_name = Path(site_dir).name
        class_name = f"{site_name.replace('-', '_').replace(' ', '').title()}LocalScraper"
        function_name = site_name.replace('-', '_').lower()

        title_selector = selectors.get('title_selector', '')
        content_selector = selectors.get('content_selector', '')
        date_selector = selectors.get('date_selector', '')
        author_selector = selectors.get('author_selector', '')

        code = f'''"""
Local scraper for {site_name}
Generated automatically from local HTML files
"""

from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Optional


class {class_name}:
    """Scraper for local HTML files in {site_dir}"""
    
    def __init__(self, site_dir: str = "{site_dir}"):
        self.site_dir = Path(site_dir)
        if not self.site_dir.exists():
            raise ValueError(f"Directory not found: {{site_dir}}")
    
    def find_html_files(self) -> List[Path]:
        """Знаходить всі HTML файли"""
        html_files = []
        for file in self.site_dir.rglob("*.html"):
            if file.name not in ["index.html", "404.html", "error.html"]:
                html_files.append(file)
        return html_files
    
    def read_file(self, filepath: Path) -> str:
        """Читає HTML файл"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {{filepath}}: {{e}}")
            return ""
    
    def scrape_article(self, filepath: Path) -> Optional[Dict]:
        """Витягує дані з локального HTML файлу"""
        html = self.read_file(filepath)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        article = {{
            'filepath': str(filepath),
            'filename': filepath.name,
            'relative_path': str(filepath.relative_to(self.site_dir)),
            'title': None,
            'content': None,
            'date': None,
            'author': None
        }}
        
        # Витягуємо заголовок
        {"title_elem = soup.select_one('" + title_selector + "')" if title_selector else "title_elem = None"}
        if title_elem:
            article['title'] = title_elem.get_text(strip=True)
        
        # Витягуємо контент
        {"content_elem = soup.select_one('" + content_selector + "')" if content_selector else "content_elem = None"}
        if content_elem:
            paragraphs = content_elem.find_all(['p', 'div'])
            if paragraphs:
                article['content'] = '\\n\\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            else:
                article['content'] = content_elem.get_text(strip=True)
        
        # Витягуємо дату
        {"date_elem = soup.select_one('" + date_selector + "')" if date_selector else "date_elem = None"}
        if date_elem:
            article['date'] = date_elem.get_text(strip=True)
        
        # Витягуємо автора
        {"author_elem = soup.select_one('" + author_selector + "')" if author_selector else "author_elem = None"}
        if author_elem:
            article['author'] = author_elem.get_text(strip=True)
        
        return article if article['title'] or article['content'] else None
    
    def scrape(self, max_articles: int = None) -> List[Dict]:
        """
        Головна функція для скрейпінгу локальних статей
        
        Args:
            max_articles: Максимальна кількість статей (None = всі)
            
        Returns:
            Список словників з даними статей
        """
        print(f"Scraping local site: {{self.site_dir}}...")
        
        html_files = self.find_html_files()
        print(f"Found {{len(html_files)}} HTML files")
        
        if max_articles:
            html_files = html_files[:max_articles]
        
        articles = []
        for i, filepath in enumerate(html_files, 1):
            print(f"Scraping file {{i}}/{{len(html_files)}}: {{filepath.name}}")
            article = self.scrape_article(filepath)
            if article:
                articles.append(article)
        
        print(f"Successfully scraped {{len(articles)}} articles")
        return articles


def scrape_{function_name}(site_dir: str = "{site_dir}", max_articles: int = None) -> List[Dict]:
    """
    Функція-обгортка для зручності використання
    
    Args:
        site_dir: Шлях до директорії з HTML файлами
        max_articles: Максимальна кількість статей
        
    Returns:
        Список статей
    """
    scraper = {class_name}(site_dir)
    return scraper.scrape(max_articles)


if __name__ == "__main__":
    articles = scrape_{function_name}(max_articles=5)
    
    print(f"\\n{{'='*50}}")
    print(f"Scraped {{len(articles)}} articles:")
    print(f"{{'='*50}}\\n")
    
    for i, article in enumerate(articles, 1):
        print(f"Article {{i}}:")
        print(f"  File: {{article['filename']}}")
        print(f"  Path: {{article['relative_path']}}")
        print(f"  Title: {{article['title']}}")
        print(f"  Date: {{article.get('date', 'N/A')}}")
        print(f"  Author: {{article.get('author', 'N/A')}}")
        print(f"  Content length: {{len(article.get('content', '')) if article.get('content') else 0}} chars")
        print()
'''

        return code

    def generate_batch(self, site_urls: list, is_local: bool = False) -> Dict:
        """
        Генерує скрейпери для списку сайтів

        Args:
            site_urls: Список URL сайтів або шляхів до локальних директорій
            is_local: True якщо це локальні директорії

        Returns:
            Словник з результатами для кожного сайту
        """
        results = {}

        for i, url in enumerate(site_urls, 1):
            print(f"\nProcessing site {i}/{len(site_urls)}")
            try:
                result = self.generate(url, is_local=is_local)
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

    # Для локальних файлів
    # result = generator.generate("sites/newsroom-hub", is_local=True)
