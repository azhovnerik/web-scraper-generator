# Task 03: Test Suite Implementation

## Objective
Create automated test suite with 5 different test sites to validate scraper generator quality.

## Test Sites Structure

### Test Sites (in external/auto-scraper-tester/sites/)
1. **arts-review-quarterly** (localhost:8888)
   - Reviews site with /reviews/ path
   - Pagination: /reviews/page/2/, /reviews/page/3/
   - Expected: 22 articles

2. **health-wellness-daily** (localhost:8889)
   - Health articles with /posts/ path
   - Special routing: homepage → /articles/ → /posts/
   - Expected: 19 articles

3. **newsroom-hub** (localhost:9021)
   - News site with /articles/ path
   - Blog listing page detection
   - Expected: 18 articles

4. **tech-insights** (localhost:9022)
   - Tech blog
   - Standard structure
   - Expected: 15 articles

5. **travel-journal-atlas** (localhost:9023)
   - Travel stories with /stories/ path
   - Relative URLs (stories/ vs /stories/)
   - Expected: 18 articles

## Implementation Tasks

### 1. Generate Scrapers for Each Site
- [x] Сгенерировать скрейпер для каждого сайта отдельно
- [x] Сохранить в external/auto-scraper-tester/src/ с уникальными именами:
  - arts_review_quarterly_scraper.py
  - health_wellness_daily_scraper.py
  - newsroom_hub_scraper.py
  - tech_insights_scraper.py
  - travel_journal_atlas_scraper.py

### 2. Update Routing Logic
- [x] Обновить main.py чтобы выбирать нужный скрейпер на основе URL
- [x] Реализовать детектирование структуры сайта:
  - По наличию /reviews/ → arts scraper
  - По наличию /posts/ на /articles/ → health scraper
  - По наличию /articles/ → newsroom scraper
  - По наличию /insights/ → tech scraper
  - По наличию /stories/ → travel scraper

### 3. Create Test Suite
- [x] Написать pytest тесты для каждого сайта
- [x] Проверка правильного количества статей
- [x] Валидация структуры данных
- [x] Проверка обязательных полей

## Test Requirements

### Test Class: TestGetArticles
```python
def test_arts_review_quarterly():
    # Should find 22 articles

def test_health_wellness_daily():
    # Should find 19 articles

def test_newsroom_hub():
    # Should find 18 articles

def test_tech_insights():
    # Should find 15 articles

def test_travel_journal_atlas():
    # Should find 18 articles
```

## Success Criteria
- [x] All 5 tests pass (5/5)
- [x] Each scraper finds correct number of articles
- [x] Articles have required fields (url, title or content)
- [x] No duplicate URLs
- [x] Proper routing based on site structure

## Known Issues & Solutions

### Issue 1: Relative URLs
**Problem**: Links like `stories/post/` not matched by `/stories/` check
**Solution**: Use `'stories/' in href` instead of `'/stories/' in href`

### Issue 2: Blog Page Path
**Problem**: Pagination uses wrong base path
**Solution**: Set `blog_page_path` correctly in metadata

### Issue 3: Nested Article Detection
**Problem**: Health site has /articles/ → /posts/ structure
**Solution**: Check /articles/ page for /posts/ links in routing

## Running Tests

```bash
# Start test servers (ports 8888, 8889, 9021-9023)
cd external/auto-scraper-tester
./start_servers.sh

# Run tests
python -m pytest tests/test_main.py -v

# Expected output: 5 passed
```
