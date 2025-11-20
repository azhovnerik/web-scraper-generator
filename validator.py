from bs4 import BeautifulSoup
from typing import Dict, List


class ScraperValidator:
    """Валідує згенеровані селектори на прикладах статей"""

    def __init__(self):
        pass

    def validate_selectors(self, selectors: Dict, homepage_html: str,
                           article_samples: List[Dict]) -> Dict:
        """Перевіряє, чи працюють селектори на даних прикладах"""
        results = {
            'article_links': self._validate_article_links(
                selectors.get('article_links_selector'),
                homepage_html
            ),
            'title': self._validate_field(
                selectors.get('title_selector'),
                article_samples,
                'title'
            ),
            'content': self._validate_field(
                selectors.get('content_selector'),
                article_samples,
                'content'
            ),
            'date': self._validate_field(
                selectors.get('date_selector'),
                article_samples,
                'date'
            ),
            'author': self._validate_field(
                selectors.get('author_selector'),
                article_samples,
                'author'
            ),
            'overall_score': 0
        }

        # ВАЖНО: article_links_selector критически важен!
        # Без него скрейпер не найдет статьи на homepage
        if not results['article_links']['found']:
            # Если selector не находит ссылки - это критическая ошибка
            results['overall_score'] = 0.0
        else:
            # Если ссылки найдены, считаем средний score
            scores = [1.0]  # За article_links
            if results['title']['success_rate'] > 0:
                scores.append(results['title']['success_rate'])
            if results['content']['success_rate'] > 0:
                scores.append(results['content']['success_rate'])

            results['overall_score'] = sum(scores) / len(scores) if scores else 0

        return results

    def _validate_article_links(self, selector: str, html: str) -> Dict:
        """Перевіряє селектор посилань на статті"""
        if not selector or not html:
            return {'found': False, 'count': 0}

        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.select(selector)
        links = [elem.get('href') for elem in elements if elem.get('href')]

        return {
            'found': len(links) > 0,
            'count': len(links),
            'examples': links[:3]
        }

    def _validate_field(self, selector: str, samples: List[Dict],
                        field_name: str) -> Dict:
        """Перевіряє селектор для конкретного поля"""
        if not selector:
            return {
                'success_rate': 0,
                'found_in': 0,
                'total': len(samples),
                'examples': []
            }

        found_count = 0
        examples = []

        for sample in samples:
            html = sample.get('html', '')
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            element = soup.select_one(selector)

            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 0:
                    found_count += 1
                    examples.append({
                        'url': sample.get('url'),
                        'value': text[:100]
                    })

        return {
            'success_rate': found_count / len(samples) if samples else 0,
            'found_in': found_count,
            'total': len(samples),
            'examples': examples
        }

    def is_valid(self, validation_results: Dict, threshold: float = 0.6) -> bool:
        """Визначає, чи валідні селектори"""
        return validation_results['overall_score'] >= threshold
