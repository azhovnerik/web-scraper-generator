from jinja2 import Template

SCRAPER_TEMPLATE = """import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin
import time


class {{ class_name }}:
    \"\"\"Scraper for {{ site_url }}\"\"\"
    
    def __init__(self):
        self.base_url = "{{ site_url }}"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url: str) -> Optional[str]:
        \"\"\"Завантажує HTML сторінки\"\"\"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_article_links(self) -> List[str]:
        \"\"\"Отримує список посилань на статті\"\"\"
        html = self.fetch_page(self.base_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        {% if article_links_selector %}
        elements = soup.select("{{ article_links_selector }}")
        for element in elements:
            href = element.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                links.append(full_url)
        {% else %}
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '{{ base_url_pattern }}' in href:
                full_url = urljoin(self.base_url, href)
                links.append(full_url)
        {% endif %}
        
        return list(set(links))
    
    def scrape_article(self, url: str) -> Optional[Dict]:
        \"\"\"Витягує дані з окремої статті\"\"\"
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        article = {
            'url': url,
            'title': None,
            'content': None,
            'date': None,
            'author': None
        }
        
        {% if title_selector %}
        title_elem = soup.select_one("{{ title_selector }}")
        if title_elem:
            article['title'] = title_elem.get_text(strip=True)
        {% endif %}
        
        {% if content_selector %}
        content_elem = soup.select_one("{{ content_selector }}")
        if content_elem:
            paragraphs = content_elem.find_all(['p', 'div'])
            if paragraphs:
                article['content'] = '\\n\\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            else:
                article['content'] = content_elem.get_text(strip=True)
        {% endif %}
        
        {% if date_selector %}
        date_elem = soup.select_one("{{ date_selector }}")
        if date_elem:
            article['date'] = date_elem.get_text(strip=True)
        {% endif %}
        
        {% if author_selector %}
        author_elem = soup.select_one("{{ author_selector }}")
        if author_elem:
            article['author'] = author_elem.get_text(strip=True)
        {% endif %}
        
        return article if article['title'] or article['content'] else None
    
    def scrape(self, max_articles: int = 10) -> List[Dict]:
        \"\"\"Головна функція для скрейпінгу статей\"\"\"
        print(f"Scraping {self.base_url}...")
        
        article_links = self.get_article_links()
        print(f"Found {len(article_links)} article links")
        
        article_links = article_links[:max_articles]
        
        articles = []
        for i, link in enumerate(article_links, 1):
            print(f"Scraping article {i}/{len(article_links)}: {link}")
            article = self.scrape_article(link)
            if article:
                articles.append(article)
            time.sleep(1)
        
        print(f"Successfully scraped {len(articles)} articles")
        return articles


def scrape_{{ function_name }}(max_articles: int = 10) -> List[Dict]:
    \"\"\"Функція-обгортка для зручності використання\"\"\"
    scraper = {{ class_name }}()
    return scraper.scrape(max_articles)


if __name__ == "__main__":
    articles = scrape_{{ function_name }}(max_articles=5)
    
    print(f"\\n{'='*50}")
    print(f"Scraped {len(articles)} articles:")
    print(f"{'='*50}\\n")
    
    for i, article in enumerate(articles, 1):
        print(f"Article {i}:")
        print(f"  URL: {article['url']}")
        print(f"  Title: {article['title']}")
        print(f"  Date: {article.get('date', 'N/A')}")
        print(f"  Author: {article.get('author', 'N/A')}")
        print(f"  Content length: {len(article.get('content', '')) if article.get('content') else 0} chars")
        print()
"""


def generate_scraper_code(site_url: str, selectors: dict) -> str:
    """Генерує код скрейпера на основі шаблону та селекторів"""
    domain = site_url.replace('https://', '').replace('http://', '').replace('www.', '')
    domain = domain.split('/')[0].replace('.', '_').replace('-', '_')
    class_name = f"{domain.title().replace('_', '')}Scraper"
    function_name = domain.lower()

    template = Template(SCRAPER_TEMPLATE)

    code = template.render(
        site_url=site_url,
        class_name=class_name,
        function_name=function_name,
        article_links_selector=selectors.get('article_links_selector', ''),
        title_selector=selectors.get('title_selector', ''),
        content_selector=selectors.get('content_selector', ''),
        date_selector=selectors.get('date_selector', ''),
        author_selector=selectors.get('author_selector', ''),
        base_url_pattern=selectors.get('base_url_pattern', '/blog/')
    )

    return code
