import os
import json
import requests
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Client for OpenRouter API to interact with LLMs"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "anthropic/claude-3.5-sonnet"

    def find_article_urls(self, site_url: str, homepage_html: str, max_articles: int = 5, is_blog_page: bool = False) -> list:
        """
        Використовує AI для пошуку посилань на конкретні статті на головній сторінці

        Args:
            site_url: Базовий URL сайту
            homepage_html: HTML головної сторінки
            max_articles: Максимальна кількість статей для повернення
            is_blog_page: Чи це сторінка блогу (дає більше HTML для аналізу)

        Returns:
            Список URL конкретних статей (не листингових сторінок)
        """
        # Для сторінок блогу беремо більше HTML
        # Збільшуємо ліміт для homepage до 40000, щоб захопити більше контенту
        limit = 50000 if is_blog_page else 40000
        homepage_preview = homepage_html[:limit] if len(homepage_html) > limit else homepage_html

        blog_hint = " (this is a blog listing page)" if is_blog_page else ""

        prompt = f"""Analyze the HTML{blog_hint} and find direct links to INDIVIDUAL ARTICLES/BLOG POSTS.

Base URL: {site_url}

HTML Content:
{homepage_preview}

Your task is to find <a href="..."> tags that link to SPECIFIC article/blog post pages, NOT listing/directory pages.

INCLUDE these types of URLs (specific articles):
- URLs with article titles: /blog/how-to-build-app/, /blog/ai-in-healthcare/
- URLs with dates: /blog/2024/01/post-name/
- URLs ending with article slugs: /reviews/movie-review/, /news/latest-update/
- Any URL that describes a SPECIFIC topic, tutorial, or story

EXCLUDE these types of URLs (listing/directory pages):
- Categories: /blog/category/tech/, /blog/categories/news/
- Tags: /blog/tag/python/, /blog/tags/ai/
- Authors: /blog/author/john/, /blog/authors/team/
- Pagination: /blog/page/2/, /page/3/
- Industry/topic directories: /blog/industries/healthcare/, /blog/topics/ai/
- Any plural noun that suggests a collection: /industries/, /topics/, /sectors/, /solutions/
- Listing pages: /blog/, /news/, /articles/ (without additional path)
- Navigation: /about/, /contact/, /services/

EXAMPLES of what to include:
- /blog/artificial-intelligence-in-oil-and-gas/ ✓ (specific topic article)
- /blog/how-to-choose-software-development-partner/ ✓ (specific tutorial)
- /reviews/dune-part-two-epic-vision/ ✓ (specific review)

EXAMPLES of what to exclude:
- /blog/categories/ai-ml/ ✗ (category listing)
- /blog/authors/john-doe/ ✗ (author listing)
- /blog/industries/healthcare/ ✗ (industry directory - listing page)
- /blog/topics/technology/ ✗ (topic directory - listing page)
- /blog/page/2/ ✗ (pagination)

KEY DISTINCTION: Include specific descriptive articles, exclude general directory/listing pages with plural nouns.

Return up to {max_articles} article URLs as JSON array:
[
  "/blog/article-1/",
  "/blog/article-2/"
]

If no articles found: []"""

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/scraper-generator",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 1000
                },
                timeout=60
            )

            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Debug: print raw response
            print(f"  LLM raw response: {content[:500]}...")

            # Parse JSON from response - multiple strategies
            json_text = None

            # Strategy 1: Look for markdown code blocks
            if "```json" in content:
                json_text = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_text = content.split("```")[1].split("```")[0].strip()
            else:
                # Strategy 2: Look for JSON array/object in text
                import re
                # Try to find JSON array
                array_match = re.search(r'\[[\s\S]*?\]', content)
                if array_match:
                    json_text = array_match.group(0)
                else:
                    # Try to find JSON object
                    object_match = re.search(r'\{[\s\S]*?\}', content)
                    if object_match:
                        json_text = object_match.group(0)

            if json_text:
                print(f"  Parsing JSON: {json_text[:200]}...")
                urls = json.loads(json_text)

                # Post-filter to remove common directory/listing page patterns
                if isinstance(urls, list):
                    filtered_urls = []
                    directory_patterns = [
                        '/industries/', '/topics/', '/sectors/', '/solutions/',
                        '/services/', '/products/', '/categories/', '/tags/',
                        '/authors/', '/archive/'
                    ]

                    for url in urls:
                        url_lower = url.lower()
                        # Check if URL contains any directory pattern
                        is_directory = any(pattern in url_lower for pattern in directory_patterns)

                        if not is_directory:
                            filtered_urls.append(url)
                        else:
                            print(f"  Filtered out directory page: {url}")

                    return filtered_urls
                else:
                    return []
            else:
                print(f"  No JSON found in response")
                return []

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from LLM: {e}")
            print(f"Attempted to parse: {json_text}")
            return []
        except Exception as e:
            print(f"Error finding article URLs with LLM: {e}")
            return []

    def analyze_site_structure(self, site_url: str, homepage_html: str,
                               article_samples: list, article_urls: list = None) -> Dict:
        """
        Аналізує структуру сайту та визначає CSS-селектори

        Args:
            site_url: URL сайту
            homepage_html: HTML головної сторінки або блог-сторінки
            article_samples: Список словників з HTML прикладів статей
            article_urls: Список URLs які AI визначив як статті

        Returns:
            Словник з CSS-селекторами
        """

        homepage_preview = homepage_html[:15000] if len(homepage_html) > 15000 else homepage_html

        articles_preview = ""
        for i, sample in enumerate(article_samples[:3], 1):
            # Беремо більше HTML з ПОЧАТКУ щоб AI міг знайти дату/автора
            article_html = sample.get('html', '')[:30000]
            # Додаємо URL для контексту
            articles_preview += f"\n\n--- Article {i} (URL: {sample.get('url', 'N/A')}) ---\n{article_html}"

        # Додаємо список URLs для аналізу паттернів
        article_urls_text = ""
        if article_urls:
            article_urls_text = f"\n\nВсі знайдені URLs статей (приклади):\n{chr(10).join(article_urls[:20])}"

        prompt = f"""Проаналізуй HTML-структуру сайту та визнач CSS-селектори для скрейпінгу статей.

URL сайту: {site_url}

HTML сторінки (перші 15000 символів):
{homepage_preview}
{article_urls_text}

Приклади статей:
{articles_preview}

ВАЖЛИВО: Проаналізуй HTML та визнач які ссылки ведуть на СТАТТІ, а які на ДИРЕКТОРІЇ/КАТЕГОРІЇ.

Наприклад:
- /blog/article-name/ - стаття ✓
- /blog/industries/healthcare/ - директорія ✗
- /blog/categories/tech/ - категорія ✗

Твоє завдання - визначити CSS-селектори:

1. **article_links_selector** - селектор який знаходить ТІЛЬКИ статті (не категорії/директорії)
   - ВАЖЛИВО: href може бути відносним (stories/...) АБО абсолютним (/stories/...)
   - Використовуй *='path/' (contains) замість ^='/path/' щоб працювало з обома варіантами
   - Використовуй :not() якщо потрібно виключити паттерни
   - Приклад: a[href*='blog/']:not([href*='industries/']) - без ведучого слешу!
   - Приклад: a[href*='reviews/']:not([href*='categories/'])

2. **title_selector** - селектор для заголовка статті
3. **content_selector** - селектор для основного тексту статті
4. **date_selector** - селектор для дати публікації
   - Шукай текст як "Published on", "Posted on", дату біля заголовка
   - Може бути meta tag, time tag, або просто span/div з текстом дати
5. **author_selector** - селектор для автора статті
   - Шукай "Author:", "By", ім'я біля заголовка
   - Може бути meta tag або звичайний елемент

Поверни ТІЛЬКИ валідний JSON без додаткового тексту:
{{
  "article_links_selector": "CSS селектор з :not() якщо потрібно",
  "title_selector": "CSS селектор або null",
  "content_selector": "CSS селектор або null",
  "date_selector": "CSS селектор або null",
  "author_selector": "CSS селектор або null",
  "base_url_pattern": "патерн URL статей",
  "notes": "короткі примітки"
}}"""

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/scraper-generator",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=60
            )

            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            selectors = json.loads(content)
            return selectors

        except Exception as e:
            print(f"Error calling LLM API: {e}")
            raise

    def refine_selectors(self, site_url: str, current_selectors: Dict,
                         validation_results: Dict) -> Dict:
        """
        Уточнює селектори на основі результатів валідації

        Args:
            site_url: URL сайту
            current_selectors: Поточні селектори
            validation_results: Результати валідації

        Returns:
            Оновлені селектори
        """

        prompt = f"""Поточні CSS-селектори для сайту {site_url} працюють неправильно.

Поточні селектори:
{json.dumps(current_selectors, indent=2, ensure_ascii=False)}

Результати валідації:
{json.dumps(validation_results, indent=2, ensure_ascii=False)}

Виправ селектори, щоб вони працювали коректно.

ВАЖЛИВО: Поверни ВСІ поля з current_selectors + виправлені селектори!

Поверни ТІЛЬКИ валідний JSON з УСІМА селекторами:
{{
  "article_links_selector": "...",
  "title_selector": "...",
  "content_selector": "...",
  "date_selector": "...",
  "author_selector": "...",
  "article_path_pattern": "...",
  "base_url_pattern": "...",
  "notes": "..."
}}"""

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                timeout=60
            )

            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            print(f"Error refining selectors: {e}")
            return current_selectors
