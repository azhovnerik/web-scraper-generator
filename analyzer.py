import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set
from pathlib import Path
import time


class SiteAnalyzer:
    """Аналізує структуру сайту для знаходження статей"""

    def __init__(self, base_url: str, is_local: bool = False):
        self.is_local = is_local

        if is_local:
            # Локальні файли
            self.base_path = Path(base_url)
            if not self.base_path.exists():
                raise ValueError(f"Directory not found: {base_url}")
            self.base_url = f"file://{self.base_path.absolute()}"
            self.domain = "local"
        else:
            # URL
            self.base_url = base_url.rstrip('/')
            self.domain = urlparse(base_url).netloc
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

    def fetch_page(self, url: str, timeout: int = 10) -> str:
        """Завантажує HTML сторінки (URL або локальний файл)"""
        if self.is_local:
            # Читання локального файлу
            try:
                filepath = Path(url) if not url.startswith('file://') else Path(url.replace('file://', ''))
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading file {url}: {e}")
                return ""
        else:
            # HTTP запит
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return ""

    def find_article_pages(self, max_pages: int = 5) -> List[str]:
        """Знаходить посилання на сторінки зі статтями"""
        if self.is_local:
            return self._find_local_html_files(max_pages)
        else:
            return self._find_url_articles(max_pages)

    def _find_local_html_files(self, max_files: int) -> List[str]:
        """Знаходить локальні HTML файли, крім кореневого index.html"""
        html_files: List[str] = []
        root_index = (self.base_path / "index.html").resolve()

        for file in self.base_path.rglob("*.html"):
            try:
                if file.resolve() == root_index:
                    continue
            except OSError:
                # Якщо неможливо вирішити шлях (наприклад, биті лінки) — пропускаємо
                continue

            html_files.append(str(file))
            if len(html_files) >= max_files:
                break

        return html_files

    def _find_url_articles(self, max_pages: int) -> List[str]:
        """Знаходить статті по URL"""
        homepage_html = self.fetch_page(self.base_url)
        if not homepage_html:
            return []

        soup = BeautifulSoup(homepage_html, 'html.parser')

        article_patterns = [
            '/blog/', '/blogs/', '/news/', '/articles/', '/posts/',
            '/insights/', '/resources/', '/stories/', '/updates/',
            '/press/', '/media/', '/publications/'
        ]

        potential_urls: Set[str] = set()

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            full_url = urljoin(self.base_url, href)

            if urlparse(full_url).netloc != self.domain:
                continue

            for pattern in article_patterns:
                if pattern in full_url.lower():
                    potential_urls.add(full_url)
                    break

            path_parts = urlparse(full_url).path.strip('/').split('/')
            if len(path_parts) >= 2:
                if path_parts[0].isdigit() and len(path_parts[0]) == 4:
                    potential_urls.add(full_url)

        article_urls = list(potential_urls)[:max_pages]

        if len(article_urls) == 0:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                full_url = urljoin(self.base_url, href)

                if urlparse(full_url).netloc == self.domain:
                    skip_patterns = ['contact', 'about', 'privacy', 'terms', '#']
                    if not any(skip in full_url.lower() for skip in skip_patterns):
                        if full_url != self.base_url and full_url != self.base_url + '/':
                            article_urls.append(full_url)
                            if len(article_urls) >= max_pages:
                                break

        return article_urls

    def get_article_samples(self, num_samples: int = 3) -> List[Dict]:
        """Отримує приклади статей для аналізу"""
        article_urls = self.find_article_pages(max_pages=num_samples * 2)

        samples = []
        for url in article_urls[:num_samples]:
            if self.is_local:
                print(f"Reading file: {Path(url).name}")
            else:
                print(f"Fetching article: {url}")

            html = self.fetch_page(url)
            if html:
                samples.append({
                    'url': url,
                    'html': html
                })

            if not self.is_local:
                time.sleep(1)  # Тільки для HTTP запитів

        return samples

    def analyze(self) -> Dict:
        """Повний аналіз сайту"""
        if self.is_local:
            print(f"Analyzing local site: {self.base_path}...")
        else:
            print(f"Analyzing {self.base_url}...")

        # Отримання головної сторінки
        if self.is_local:
            index_file = self.base_path / "index.html"
            if index_file.exists():
                homepage_html = self.fetch_page(str(index_file))
            else:
                # Використовуємо першу статтю
                samples = self.get_article_samples(num_samples=1)
                homepage_html = samples[0]['html'] if samples else ""
        else:
            homepage_html = self.fetch_page(self.base_url)

        article_samples = self.get_article_samples(num_samples=3)

        return {
            'base_url': self.base_url,
            'is_local': self.is_local,
            'homepage_html': homepage_html,
            'article_samples': article_samples,
            'num_samples': len(article_samples)
        }
