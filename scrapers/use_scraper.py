from scrapers.anadea_info_scraper import scrape_anadea_info

# Отримуємо статті
articles = scrape_anadea_info(max_articles=10)

# Обробляємо результати
for article in articles:
    print(f"Title: {article['title']}")
    print(f"URL: {article['url']}")
    print(f"Date: {article.get('date', 'N/A')}")
    print(f"Content length: {len(article.get('content', ''))}")
    print("-" * 50)
