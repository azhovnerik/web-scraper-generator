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

    def analyze_site_structure(self, site_url: str, homepage_html: str,
                               article_samples: list) -> Dict:
        """
        Аналізує структуру сайту та визначає CSS-селектори

        Args:
            site_url: URL сайту
            homepage_html: HTML головної сторінки
            article_samples: Список словників з HTML прикладів статей

        Returns:
            Словник з CSS-селекторами
        """

        homepage_preview = homepage_html[:15000] if len(homepage_html) > 15000 else homepage_html

        articles_preview = ""
        for i, sample in enumerate(article_samples[:3], 1):
            article_html = sample.get('html', '')[:10000]
            articles_preview += f"\n\n--- Article {i} (URL: {sample.get('url', 'N/A')}) ---\n{article_html}"

        prompt = f"""Проаналізуй HTML-структуру сайту та визнач CSS-селектори для скрейпінгу статей.

URL сайту: {site_url}

HTML головної сторінки (перші 15000 символів):
{homepage_preview}

Приклади статей:
{articles_preview}

Твоє завдання - визначити CSS-селектори для наступних елементів:

1. **article_links_selector** - селектор для знаходження посилань на статті на головній сторінці
2. **title_selector** - селектор для заголовка статті на сторінці статті
3. **content_selector** - селектор для основного тексту статті
4. **date_selector** - селектор для дати публікації (якщо є)
5. **author_selector** - селектор для автора статті (якщо є)

Важливо:
- Селектори повинні бути максимально специфічними
- Якщо елемент не знайдено, вкажи null
- Для article_links_selector враховуй навігацію до /blog/, /news/, /articles/

Поверни ТІЛЬКИ валідний JSON без додаткового тексту:
{{
  "article_links_selector": "CSS селектор або null",
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

Поверни ТІЛЬКИ валідний JSON з оновленими селекторами:
{{
  "article_links_selector": "...",
  "title_selector": "...",
  "content_selector": "...",
  "date_selector": "...",
  "author_selector": "..."
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
