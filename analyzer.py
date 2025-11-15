import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set
import time


class SiteAnalyzer:
    """Аналізує структуру сайту для знаходження статей"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_page(self, url: str, timeout: int = 10) -> str:
        """Завантажує HTML сторінки"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def find_article_pages(self, max_pages: int = 5) -> List[str]:
        """
        Знаходить посилання на сторінки зі статтями

        Returns:
            Список URL сторінок статей
        """
        homepage_html = self.fetch_page(self.base_url)
        if not homepage_html:
            return []

        soup = BeautifulSoup(homepage_html, 'html.parser')

        # Типові патерни для блогів та статей
        article_patterns = [
            '/blog/', '/blogs/', '/news/', '/articles/', '/posts/',
            '/insights/', '/resources/', '/stories/', '/updates/',
            '/press/', '/media/', '/publications/'
        ]

        potential_urls: Set[str] = set()

        # Шукаємо посилання
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            full_url = urljoin(self.base_url, href)

            # Перевіряємо, чи це посилання на той самий домен
            if urlparse(full_url).netloc != self.domain:
                continue

            # Шукаємо патерни
            for pattern in article_patterns:
                if pattern in full_url.lower():
                    potential_urls.add(full_url)
                    break

            # Шукаємо за структурою URL (наприклад, /2024/11/article-name)
            path_parts = urlparse(full_url).path.strip('/').split('/')
            if len(path_parts) >= 2:
                # Можливо це дата в URL
                if path_parts[0].isdigit() and len(path_parts[0]) == 4:
                    potential_urls.add(full_url)

        # Обмежуємо кількість
        article_urls = list(potential_urls)[:max_pages]

        # Якщо не знайшли, спробуємо знайти будь-які внутрішні посилання
        if len(article_urls) == 0:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                full_url = urljoin(self.base_url, href)

                if urlparse(full_url).netloc == self.domain:
                    # Пропускаємо головну, контакти, about тощо
                    skip_patterns = ['contact', 'about', 'privacy', 'terms', '#']
                    if not any(skip in full_url.lower() for skip in skip_patterns):
                        if full_url != self.base_url and full_url != self.base_url + '/':
                            article_urls.append(full_url)
                            if len(article_urls) >= max_pages:
                                break

        return article_urls

    def get_article_samples(self, num_samples: int = 3) -> List[Dict]:
        """
        Отримує приклади статей для аналізу

        Returns:
            Список словників з URL та HTML статей
        """
        article_urls = self.find_article_pages(max_pages=num_samples * 2)

        samples = []
        for url in article_urls[:num_samples]:
            print(f"Fetching article: {url}")
            html = self.fetch_page(url)
            if html:
                samples.append({
                    'url': url,
                    'html': html
                })
            time.sleep(1)  # Бути ввічливими до сервера

        return samples

    def analyze(self) -> Dict:
        """
        Повний аналіз сайту

        Returns:
            Словник з даними про сайт
        """
        print(f"Analyzing {self.base_url}...")

        homepage_html = self.fetch_page(self.base_url)
        article_samples = self.get_article_samples(num_samples=3)

        return {
            'base_url': self.base_url,
            'homepage_html': homepage_html,
            'article_samples': article_samples,
            'num_samples': len(article_samples)
        }
