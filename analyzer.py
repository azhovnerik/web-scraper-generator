import time
from typing import List, Dict
from urllib.parse import urljoin, urlparse

import requests

from llm_client import LLMClient


class SiteAnalyzer:
    """Аналізує структуру сайту для знаходження статей використовуючи AI"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.llm_client = LLMClient()

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
        """Використовує AI для знаходження посилань на конкретні статті"""
        homepage_html = self.fetch_page(self.base_url)
        if not homepage_html:
            return []

        print(f"  Using AI to find article URLs on homepage...")

        # Використовуємо LLM для пошуку статей на homepage
        article_urls_relative = self.llm_client.find_article_urls(
            site_url=self.base_url,
            homepage_html=homepage_html,
            max_articles=max_pages
        )

        # Завжди перевіряємо наявність окремої сторінки блогу
        print(f"  Checking for dedicated blog page...")
        blog_page_url = self._find_blog_page(homepage_html)

        if blog_page_url:
            print(f"  Found blog page: {blog_page_url}")
            blog_html = self.fetch_page(blog_page_url)
            if blog_html:
                print(f"  Blog page HTML length: {len(blog_html)} chars")
                # Збільшуємо кількість статей для кращого аналізу
                blog_article_urls = self.llm_client.find_article_urls(
                    site_url=blog_page_url,
                    homepage_html=blog_html,
                    max_articles=30,  # Більше статей для кращого аналізу паттернів
                    is_blog_page=True
                )

                # Додаємо blog articles до списку (пріоритет blog articles)
                if len(blog_article_urls) > 0:
                    print(f"  Found {len(blog_article_urls)} blog articles, using those")
                    article_urls_relative = blog_article_urls
                elif len(article_urls_relative) == 0:
                    # Якщо не знайшли нічого ні на homepage, ні на blog
                    article_urls_relative = []

        # Конвертуємо відносні URL в абсолютні
        article_urls = []
        for url in article_urls_relative:
            if url.startswith('http'):
                full_url = url
            else:
                full_url = urljoin(self.base_url, url)

            # Перевіряємо що це той самий домен
            if urlparse(full_url).netloc == self.domain or urlparse(full_url).netloc == '':
                article_urls.append(full_url)

        print(f"  AI found {len(article_urls)} article URLs")

        return article_urls[:max_pages]

    def _find_blog_page(self, homepage_html: str) -> str:
        """Знаходить посилання на сторінку блогу (листингову, не конкретну статтю)"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(homepage_html, 'html.parser')

        # Шукаємо посилання з патернами блогу
        blog_patterns = ['/blog/', '/news/', '/articles/', '/posts/', '/insights/', '/resources/', '/guides/', '/reviews/']

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            href_lower = href.lower().rstrip('/')  # Remove trailing slash for comparison

            for pattern in blog_patterns:
                pattern_clean = pattern.rstrip('/')
                # Шукаємо ТОЧНО листингові сторінки
                # href must end exactly with pattern (no extra path segments after)
                if (href_lower == pattern_clean or  # Exact match like "/articles"
                    href_lower.endswith(pattern_clean) and  # Ends with pattern
                    href_lower.count('/') == pattern_clean.count('/')  # Same number of slashes = no extra segments
                   ):
                    if not any(skip in href_lower for skip in ['#', 'category', 'tag', 'page']):
                        full_url = urljoin(self.base_url, href)
                        # Verify it's actually a listing page by fetching it
                        try:
                            test_response = self.session.get(full_url, timeout=5)
                            if test_response.status_code == 200:
                                # Check if page has multiple article links (indicating it's a listing page)
                                test_soup = BeautifulSoup(test_response.text, 'html.parser')
                                article_links = [a for a in test_soup.find_all('a', href=True)
                                               if any(p in a.get('href', '').lower() for p in ['/blog/', '/news/', '/articles/', '/posts/', '/reviews/', '/stories/', '/guides/'])]
                                if len(article_links) >= 3:  # At least 3 article links = listing page
                                    return full_url
                        except:
                            continue

        # Fallback: если не нашли ссылку на homepage, пробуем напрямую проверить стандартные пути
        print("  Blog page not found in homepage links, trying direct paths...")
        for pattern in blog_patterns:
            try:
                test_url = urljoin(self.base_url, pattern)
                test_response = self.session.get(test_url, timeout=5)
                if test_response.status_code == 200:
                    # Check if page has multiple article links
                    test_soup = BeautifulSoup(test_response.text, 'html.parser')
                    article_links = [a for a in test_soup.find_all('a', href=True)
                                   if any(p in a.get('href', '').lower() for p in ['/blog/', '/news/', '/articles/', '/posts/', '/reviews/', '/stories/', '/guides/'])]
                    if len(article_links) >= 3:  # At least 3 article links = listing page
                        print(f"  Found blog page via direct path: {test_url}")
                        return test_url
            except:
                continue

        return None

    def get_article_samples(self, num_samples: int = 3) -> List[Dict]:
        """Отримує приклади статей для аналізу"""
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

            time.sleep(1)

        return samples

    def analyze(self) -> Dict:
        """Повний аналіз сайту"""
        print(f"Analyzing {self.base_url}...")

        homepage_html = self.fetch_page(self.base_url)

        # Знаходимо blog page якщо є
        blog_page_html = None
        blog_page_url = self._find_blog_page(homepage_html)
        if blog_page_url:
            blog_page_html = self.fetch_page(blog_page_url)
            if blog_page_html:
                print(f"  Found blog page for validation: {blog_page_url}")

        # Отримуємо список всіх URLs статей для аналізу паттернів
        article_urls = self.find_article_pages(max_pages=30)
        # Збільшуємо кількість прикладів статей для кращого аналізу date/author
        article_samples = self.get_article_samples(num_samples=5)

        return {
            'base_url': self.base_url,
            'homepage_html': homepage_html,
            'blog_page_html': blog_page_html,  # HTML blog page для валідації
            'blog_page_url': blog_page_url,
            'article_urls': article_urls,  # Повний список URLs для AI аналізу
            'article_samples': article_samples,
            'num_samples': len(article_samples)
        }
