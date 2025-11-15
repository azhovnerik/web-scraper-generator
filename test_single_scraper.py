#!/usr/bin/env python3
"""
Скрипт для тестування окремого скрейпера
Використовуйте для швидкої перевірки згенерованого скрейпера

Usage:
    python test_single_scraper.py scrapers/anadea_info_scraper.py
"""

import sys
import importlib.util
from pathlib import Path


def load_scraper(filepath):
    """Завантажує модуль скрейпера"""
    spec = importlib.util.spec_from_file_location("scraper", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scraper(filepath, max_articles=3):
    """Тестує скрейпер"""
    print(f"{'='*60}")
    print(f"Testing scraper: {filepath}")
    print(f"{'='*60}\n")

    # Завантажуємо модуль
    try:
        module = load_scraper(filepath)
    except Exception as e:
        print(f"❌ Error loading module: {e}")
        return False

    # Знаходимо функцію scrape_*
    scrape_func = None
    for attr in dir(module):
        if attr.startswith('scrape_') and callable(getattr(module, attr)):
            scrape_func = getattr(module, attr)
            break

    if not scrape_func:
        print("❌ No scrape_* function found in module")
        return False

    print(f"✓ Found scrape function: {scrape_func.__name__}")

    # Викликаємо скрейпер
    print(f"\nScraping {max_articles} articles...\n")

    try:
        articles = scrape_func(max_articles=max_articles)
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Перевіряємо результати
    if not articles:
        print("❌ No articles returned")
        return False

    print(f"\n{'='*60}")
    print(f"✓ Successfully scraped {len(articles)} articles")
    print(f"{'='*60}\n")

    # Показуємо результати
    for i, article in enumerate(articles, 1):
        print(f"Article {i}:")
        print(f"  URL: {article.get('url', 'N/A')}")
        print(f"  Title: {article.get('title', 'N/A')[:80]}...")
        print(f"  Content length: {len(article.get('content', '')) if article.get('content') else 0} chars")
        print(f"  Date: {article.get('date', 'N/A')}")
        print(f"  Author: {article.get('author', 'N/A')}")

        # Перевірка обов'язкових полів
        if not article.get('url'):
            print("  ⚠️  Warning: Missing URL")
        if not article.get('title') and not article.get('content'):
            print("  ⚠️  Warning: Missing both title and content")

        print()

    # Статистика
    print(f"{'='*60}")
    print("Statistics:")
    print(f"  Total articles: {len(articles)}")
    print(f"  With title: {sum(1 for a in articles if a.get('title'))}")
    print(f"  With content: {sum(1 for a in articles if a.get('content'))}")
    print(f"  With date: {sum(1 for a in articles if a.get('date'))}")
    print(f"  With author: {sum(1 for a in articles if a.get('author'))}")

    avg_content_length = sum(len(a.get('content', '')) for a in articles) / len(articles)
    print(f"  Avg content length: {avg_content_length:.0f} chars")
    print(f"{'='*60}\n")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_single_scraper.py <scraper_file.py> [max_articles]")
        print("\nExample:")
        print("  python test_single_scraper.py scrapers/anadea_info_scraper.py")
        print("  python test_single_scraper.py scrapers/anadea_info_scraper.py 5")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    max_articles = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    success = test_scraper(filepath, max_articles)

    if success:
        print("✅ Test passed!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
