# 📂 Структура проекту

```
scraper-generator/
│
├── 📄 README.md                    # Головна документація проекту
├── 📄 QUICK_START.md              # Швидкий старт для новачків
├── 📄 FAQ.md                      # Часті питання та відповіді
├── 📄 SUBMISSION_GUIDE.md         # Інструкція для здачі завдання
├── 📄 PROJECT_STRUCTURE.md        # Цей файл - опис структури
│
├── ⚙️ requirements.txt             # Python залежності
├── ⚙️ .env.example                 # Приклад конфігурації (без секретів)
├── ⚙️ .env                         # Реальна конфігурація (НЕ коміть!)
├── ⚙️ .gitignore                   # Файли для ігнорування в Git
├── ⚙️ pytest.ini                   # Конфігурація pytest
├── ⚙️ Makefile                     # Команди для автоматизації
├── 🔧 setup.sh                     # Скрипт налаштування проекту
│
├── 🐍 CORE MODULES (головна логіка)
│   ├── analyzer.py                # Аналіз структури сайту
│   ├── llm_client.py             # Клієнт для OpenRouter API
│   ├── template.py               # Jinja2 шаблон скрейпера
│   ├── validator.py              # Валідація CSS-селекторів
│   └── generator.py              # Головний генератор
│
├── 🚀 ENTRY POINTS (точки входу)
│   ├── main.py                   # CLI для генерації скрейперів
│   ├── test_single_scraper.py   # Тестування одного скрейпера
│   └── run_all_scrapers.py      # Запуск всіх згенерованих скрейперів
│
├── 📁 scrapers/                   # Згенеровані скрейпери
│   ├── *.py                      # Файли скрейперів
│   ├── *_metadata.json           # Метадані кожного скрейпера
│   └── generation_report.json   # Загальний звіт генерації
│
├── 🧪 tests/                      # Тести
│   ├── __init__.py
│   └── test_scrapers.py         # Тести для скрейперів
│
├── 📚 examples/                   # Приклади
│   └── example_scraper_output.py # Приклад згенерованого коду
│
└── 🗂️ venv/                       # Віртуальне середовище (НЕ коміть!)
    └── ...
```

## 📝 Опис файлів

### 📄 Документація

#### README.md
Головний файл документації з:
- Описом проекту
- Інструкціями з встановлення
- Прикладами використання
- Структурою проекту
- Інформацією про тести

#### QUICK_START.md
Швидкий старт для новачків:
- Покрокова інструкція встановлення
- Приклади перших команд
- Типові проблеми та їх вирішення

#### FAQ.md
Відповіді на часті питання:
- Загальні питання
- Технічні проблеми
- Troubleshooting
- Корисні команди

#### SUBMISSION_GUIDE.md
Інструкція для здачі завдання:
- Чек-лист перед здачею
- Процес завантаження на GitHub
- Критерії оцінювання
- Що робити у разі проблем

### ⚙️ Конфігурація

#### requirements.txt
Список Python залежностей:
```
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
jinja2==3.1.2
pytest==7.4.3
python-dotenv==1.0.0
httpx==0.25.2
```

#### .env.example
Приклад файлу конфігурації (безпечний для Git):
```
OPENROUTER_API_KEY=your_api_key_here
```

#### .env
Реальні секрети (НЕ повинен бути в Git!):
```
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```

#### .gitignore
Список файлів які Git ігнорує:
- `venv/` - віртуальне середовище
- `__pycache__/` - Python кеш
- `.env` - секрети
- `*.pyc` - скомпільовані файли

### 🐍 Core Modules

#### analyzer.py
**Призначення:** Аналіз структури сайту

**Ключові класи:**
- `SiteAnalyzer` - головний клас аналізатора

**Ключові методи:**
- `fetch_page(url)` - завантаження HTML
- `find_article_pages()` - пошук сторінок зі статтями
- `get_article_samples()` - отримання прикладів статей
- `analyze()` - повний аналіз сайту

**Використання:**
```python
analyzer = SiteAnalyzer("https://example.com")
analysis = analyzer.analyze()
```

#### llm_client.py
**Призначення:** Взаємодія з OpenRouter API

**Ключові класи:**
- `LLMClient` - клієнт для API

**Ключові методи:**
- `analyze_site_structure()` - аналіз HTML через LLM
- `refine_selectors()` - уточнення селекторів

**Використання:**
```python
client = LLMClient()
selectors = client.analyze_site_structure(url, html, samples)
```

#### template.py
**Призначення:** Генерація Python коду скрейпера

**Ключові функції:**
- `generate_scraper_code()` - генерує код з шаблону

**Шаблон:** Jinja2 template з placeholder'ами для:
- CSS селекторів
- URL сайту
- Імені класу/функції

**Використання:**
```python
from template import generate_scraper_code
code = generate_scraper_code(url, selectors)
```

#### validator.py
**Призначення:** Валідація CSS-селекторів

**Ключові класи:**
- `ScraperValidator` - валідатор

**Ключові методи:**
- `validate_selectors()` - перевірка селекторів
- `is_valid()` - чи пройшла валідація

**Використання:**
```python
validator = ScraperValidator()
results = validator.validate_selectors(selectors, html, samples)
```

#### generator.py
**Призначення:** Головний генератор скрейперів

**Ключові класи:**
- `ScraperGenerator` - оркеструє весь процес

**Ключові методи:**
- `generate(url)` - генерує скрейпер для одного сайту
- `generate_batch(urls)` - генерує для списку сайтів

**Workflow:**
1. Аналіз сайту (analyzer)
2. Генерація селекторів (llm_client)
3. Валідація (validator)
4. Уточнення при потребі (llm_client)
5. Генерація коду (template)
6. Збереження файлів

### 🚀 Entry Points

#### main.py
**Призначення:** CLI інтерфейс

**Команди:**
```bash
python main.py --url <URL>           # Один сайт
python main.py --batch               # Всі тестові сайти
python main.py --test-sites          # Показати список
python main.py --help                # Довідка
```

**Параметри:**
- `--output` - директорія для скрейперів
- `--max-retries` - кількість спроб уточнення

#### test_single_scraper.py
**Призначення:** Швидке тестування одного скрейпера

**Використання:**
```bash
python test_single_scraper.py scrapers/anadea_info_scraper.py
python test_single_scraper.py scrapers/anadea_info_scraper.py 5
```

**Що тестує:**
- Чи завантажується модуль
- Чи працює функція scrape_*
- Чи повертаються дані
- Статистику результатів

#### run_all_scrapers.py
**Призначення:** Запуск всіх згенерованих скрейперів

**Використання:**
```bash
python run_all_scrapers.py
python run_all_scrapers.py --max-articles 5
python run_all_scrapers.py --output results.json
```

**Що робить:**
- Знаходить всі скрейпери
- Запускає кожен
- Збирає статистику
- Зберігає результати в JSON

### 📁 scrapers/

Директорія зі згенерованими скрейперами.

**Файли:**
- `{site_name}_scraper.py` - код скрейпера
- `{site_name}_metadata.json` - метадані (селектори, validation score)
- `generation_report.json` - загальний звіт

**Приклад структури скрейпера:**
```python
class AnaDeaInfoScraper:
    def __init__(self): ...
    def fetch_page(self, url): ...
    def get_article_links(self): ...
    def scrape_article(self, url): ...
    def scrape(self, max_articles): ...

def scrape_anadea_info(max_articles=10):
    scraper = AnaDeaInfoScraper()
    return scraper.scrape(max_articles)
```

### 🧪 tests/

Директорія з тестами.

**test_scrapers.py:**
- `test_scraper_structure` - перевірка структури коду
- `test_scraper_returns_data` - чи повертаються дані
- `test_article_fields` - перевірка полів статей
- `test_no_duplicates` - перевірка на дублікати

**Запуск:**
```bash
pytest tests/test_scrapers.py -v
```

## 🔄 Workflow генерації скрейпера

```
1. USER INPUT
   ↓
   main.py --url https://example.com

2. ANALYSIS
   ↓
   analyzer.py
   - fetch homepage
   - find article links
   - fetch 3 article samples

3. LLM GENERATION
   ↓
   llm_client.py
   - send HTML to LLM
   - receive CSS selectors

4. VALIDATION
   ↓
   validator.py
   - test selectors on samples
   - calculate validation score

5. REFINEMENT (if needed)
   ↓
   llm_client.py
   - refine selectors
   - validate again

6. CODE GENERATION
   ↓
   template.py
   - use Jinja2 template
   - substitute selectors
   - generate Python code

7. SAVE
   ↓
   scrapers/
   - {site}_scraper.py
   - {site}_metadata.json
```

## 🎯 Використання згенерованого скрейпера

```python
# Варіант 1: Імпорт функції
from scrapers.anadea_info_scraper import scrape_anadea_info
articles = scrape_anadea_info(max_articles=10)

# Варіант 2: Імпорт класу
from scrapers.anadea_info_scraper import AnaDeaInfoScraper
scraper = AnaDeaInfoScraper()
articles = scraper.scrape(max_articles=10)

# Варіант 3: Прямий запуск
cd scrapers
python anadea_info_scraper.py
```

## 📊 Формат даних

**Вхід (analysis):**
```python
{
    'base_url': 'https://example.com',
    'homepage_html': '<html>...</html>',
    'article_samples': [
        {
            'url': 'https://example.com/article-1',
            'html': '<html>...</html>'
        },
        ...
    ],
    'num_samples': 3
}
```

**Проміжні дані (selectors):**
```python
{
    'article_links_selector': 'article.post a',
    'title_selector': 'h1.title',
    'content_selector': 'div.content',
    'date_selector': 'time.published',
    'author_selector': 'span.author',
    'base_url_pattern': '/blog/'
}
```

**Вихід (article):**
```python
{
    'url': 'https://example.com/article',
    'title': 'Article Title',
    'content': 'Long article text...',
    'date': '2024-11-13',
    'author': 'John Doe'
}
```

## 🛠️ Розширення проекту

### Додати нове поле (наприклад, теги):

1. **llm_client.py** - додати в промпт:
```python
7. **tags_selector** - селектор для тегів
```

2. **template.py** - додати в шаблон:
```python
# Витягуємо теги
tags_elems = soup.select("{{ tags_selector }}")
article['tags'] = [tag.get_text(strip=True) for tag in tags_elems]
```

3. **validator.py** - додати валідацію:
```python
'tags': self._validate_field(
    selectors.get('tags_selector'), 
    article_samples, 
    'tags'
)
```

### Додати підтримку JavaScript сайтів:

Замінити `requests` на `playwright` або `selenium` в шаблоні.

### Додати збереження в БД:

Додати в кінець згенерованого скрейпера код для збереження в БД.

---

**Питання? Перегляньте FAQ.md або створіть issue!**