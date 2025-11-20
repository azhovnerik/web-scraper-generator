from jinja2 import Template

SCRAPER_TEMPLATE = """\"\"\"
{{ site_name }} Scraper
Generated for: {{ site_url }}
\"\"\"

import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
from dataclasses import dataclass
import time


@dataclass
class Article:
    \"\"\"Article data structure\"\"\"
    url: str
    title: str
    author: str = ""
    published: str = ""
    content: str = ""


class {{ class_name }}:
    \"\"\"Scraper for {{ site_name }}\"\"\"

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_page(self, url: str) -> Optional[str]:
        \"\"\"Fetches HTML page\"\"\"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def get_article_links(self) -> List[str]:
        \"\"\"Gets all article links from homepage and paginated pages\"\"\"
        links = []

        # Get links from homepage
        html = self.fetch_page(self.base_url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            {% if article_links_selector %}
            elements = soup.select("{{ article_links_selector }}")
            for element in elements:
                href = element.get('href')
                if href and '{{ article_path_pattern }}'.lstrip('/') in href and not href.endswith('{{ article_path_pattern }}'):
                    # Skip category, tag, pagination, and author pages
                    if any(skip in href.lower() for skip in ['/category/', '/categories/', '/tag/', '/tags/', '/page/', '/author/', '/authors/']):
                        continue
                    full_url = urljoin(self.base_url, href)
                    links.append(full_url)
            {% else %}
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '{{ article_path_pattern }}'.lstrip('/') in href:
                    full_url = urljoin(self.base_url, href)
                    links.append(full_url)
            {% endif %}

        # Get links from paginated pages
        {% if pagination_enabled %}
        for page_num in range(1, {{ max_pagination_pages }}):
            if page_num == 1:
                paginated_url = urljoin(self.base_url, '{{ blog_page_path }}')
            else:
                # Handle root path case: if blog_page_path is '/', use '/page/X' instead of '//page/X'
                {% if blog_page_path == '/' %}
                paginated_url = urljoin(self.base_url, f'/page/{page_num}/')
                {% else %}
                paginated_url = urljoin(self.base_url, f'{{ blog_page_path }}/page/{page_num}/')
                {% endif %}

            html = self.fetch_page(paginated_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                {% if pagination_article_selector %}
                elements = soup.select("{{ pagination_article_selector }}")
                {% elif article_links_selector %}
                elements = soup.select("{{ article_links_selector }}")
                {% else %}
                elements = soup.select(".review-item h3 a, article h3 a")
                {% endif %}
                for element in elements:
                    href = element.get('href')
                    if href and '{{ article_path_pattern }}'.lstrip('/') in href and not href.endswith('{{ article_path_pattern }}'):
                        # Skip category, tag, pagination, and author pages
                        if any(skip in href.lower() for skip in ['/category/', '/categories/', '/tag/', '/tags/', '/page/', '/author/', '/authors/']):
                            continue
                        full_url = urljoin(self.base_url, href)
                        links.append(full_url)
        {% endif %}

        return list(set(links))

    def scrape_article(self, url: str) -> Optional[Article]:
        \"\"\"Extracts data from a single article\"\"\"
        html = self.fetch_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Title
        title = None
        {% if title_selector %}
        title_elem = soup.select_one("{{ title_selector }}")
        if title_elem:
            title = title_elem.get_text(strip=True)
        {% endif %}

        # Content - get full article content
        content = None
        {% if content_selector %}
        content_elem = soup.select_one("{{ content_selector }}")
        if content_elem:
            paragraphs = content_elem.find_all(['p'])
            if paragraphs:
                content = '\\n\\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            else:
                content = content_elem.get_text(strip=True)
        {% endif %}

        # Date and Author from meta
        author = ""
        published = ""

        {% if date_selector %}
        # Extract published date
        date_elem = soup.select_one("{{ date_selector }}")
        if date_elem:
            # Check if it's a meta tag (has 'content' attribute)
            if date_elem.name == 'meta':
                published = date_elem.get('content', '')
            else:
                published = date_elem.get_text(strip=True)
        {% endif %}

        {% if author_selector %}
        # Extract author
        author_elem = soup.select_one("{{ author_selector }}")
        if author_elem:
            # Check if it's a meta tag (has 'content' attribute)
            if author_elem.name == 'meta':
                author = author_elem.get('content', '')
            else:
                author = author_elem.get_text(strip=True)
        {% endif %}

        if not title and not content:
            return None

        return Article(
            url=url,
            title=title or "",
            author=author,
            published=published,
            content=content or ""
        )

    def scrape(self, max_articles: int = 100) -> List[Article]:
        \"\"\"Main scraping function\"\"\"
        print(f"Scraping {self.base_url}...")

        article_links = self.get_article_links()
        print(f"Found {len(article_links)} article links")

        if max_articles:
            article_links = article_links[:max_articles]

        articles = []
        for i, link in enumerate(article_links, 1):
            print(f"Scraping article {i}/{len(article_links)}: {link}")
            article = self.scrape_article(link)
            if article:
                articles.append(article)
            # Small delay to be respectful
            time.sleep(0.1)

        print(f"Successfully scraped {len(articles)} articles")
        return articles


def get_articles(homepage_url: str) -> List[Article]:
    \"\"\"
    Main function to get articles from {{ site_name }}.

    Args:
        homepage_url: The base URL of the website

    Returns:
        List of Article objects
    \"\"\"
    scraper = {{ class_name }}(homepage_url)
    return scraper.scrape(max_articles=100)


if __name__ == "__main__":
    # Example usage
    articles = get_articles("{{ site_url }}")

    print(f"\\n{'='*50}")
    print(f"Scraped {len(articles)} articles:")
    print(f"{'='*50}\\n")

    for i, article in enumerate(articles, 1):
        print(f"Article {i}:")
        print(f"  URL: {article.url}")
        print(f"  Title: {article.title}")
        print(f"  Author: {article.author}")
        print(f"  Published: {article.published}")
        print(f"  Content length: {len(article.content)} chars")
        print()
"""


def generate_scraper_code(site_url: str, selectors: dict) -> str:
    """Генерує код скрейпера на основі шаблону та селекторів"""
    domain = site_url.replace('https://', '').replace('http://', '').replace('www.', '')
    domain = domain.split('/')[0]

    # Обробка localhost - використовуємо "local_site" замість "localhost:port"
    if domain.startswith('localhost'):
        domain = 'local_site'
        site_name = selectors.get('site_name', 'Local Site')
    else:
        # Заміна недопустимих символів для звичайних доменів
        domain = domain.replace('.', '_').replace('-', '_').replace(':', '_')
        site_name = selectors.get('site_name', domain.replace('_', ' ').title())

    class_name = f"{domain.title().replace('_', '')}Scraper"
    function_name = domain.lower()

    template = Template(SCRAPER_TEMPLATE)

    # Determine article path pattern from base_url_pattern or article_links
    article_path_pattern = selectors.get('article_path_pattern', selectors.get('base_url_pattern', '/blog/'))

    # Enable pagination by default for most sites
    pagination_enabled = selectors.get('pagination_enabled', True)
    max_pagination_pages = selectors.get('max_pagination_pages', 4)

    # Use blog_page_path for pagination if available, otherwise use article_path_pattern
    blog_page_path = selectors.get('blog_page_path', article_path_pattern)

    code = template.render(
        site_url=site_url,
        site_name=site_name,
        class_name=class_name,
        function_name=function_name,
        article_links_selector=selectors.get('article_links_selector', ''),
        title_selector=selectors.get('title_selector', ''),
        content_selector=selectors.get('content_selector', ''),
        date_selector=selectors.get('date_selector', ''),
        author_selector=selectors.get('author_selector', ''),
        article_path_pattern=article_path_pattern,
        blog_page_path=blog_page_path,
        pagination_enabled=pagination_enabled,
        max_pagination_pages=max_pagination_pages,
        pagination_article_selector=selectors.get('pagination_article_selector', '')
    )

    return code
