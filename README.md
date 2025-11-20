# Web Scraper Generator

AI-powered Python web scraper generator that automatically creates custom scrapers for article-based websites using LLM analysis.

## Features

- **Automatic Site Analysis**: Uses AI to analyze website structure and identify article patterns
- **Smart Selector Generation**: LLM-powered CSS selector generation with automatic validation
- **Blog Page Detection**: Automatically finds blog/news/articles pages with fallback strategies
- **SPA Detection**: Identifies JavaScript-rendered sites (React/Vue/Angular) and provides helpful feedback
- **High Success Rate**: Handles both relative and absolute URLs, pagination patterns, and various site structures
- **Ready-to-Use Code**: Generates production-ready Python scrapers with comprehensive error handling
- **Automated Testing**: Includes test suite with 5 different site types

## Requirements

- Python 3.8+
- OpenRouter API key (https://openrouter.ai/)

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd web-scraper-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file with your API key:
```bash
OPENROUTER_API_KEY=your_key_here
```

## Usage

### Generate scraper for a website

```bash
python main.py --url https://example.com/blog/
```

### Examples

```bash
# Generate scraper for a blog
python main.py --url https://www.thefamilylawco.co.uk

# Generate scraper for reviews site
python main.py --url https://anadea.info
```

## Project Structure

```
web-scraper-generator/
├── analyzer.py              # Site structure analysis with AI
├── llm_client.py           # OpenRouter API client
├── template.py             # Jinja2 scraper template
├── validator.py            # Selector validation
├── generator.py            # Main generator with SPA detection
├── main.py                 # CLI interface
├── requirements.txt        # Dependencies
├── .env                    # Configuration (create from .env.example)
│
├── scrapers/               # Generated scrapers
│   ├── *_scraper.py
│   └── *_metadata.json
│
├── external/auto-scraper-tester/    # Test suite
│   ├── sites/              # 5 test websites
│   ├── src/                # Generated test scrapers
│   └── tests/              # Automated tests
│
└── utilities/
    ├── test_single_scraper.py      # Test individual scraper
    └── run_all_scrapers.py         # Batch scraper testing
```

## Testing

Run the automated test suite (requires test sites to be running):

```bash
cd external/auto-scraper-tester
python -m pytest tests/test_main.py -v
```

All 5 tests should pass:
- ✅ arts-review-quarterly (22/22 articles)
- ✅ health-wellness-daily (19/19 articles)
- ✅ newsroom-hub (18/18 articles)
- ✅ tech-insights (15/15 articles)
- ✅ travel-journal-atlas (18/18 articles)

## How It Works

1. **Site Analysis**: Fetches homepage and analyzes HTML structure
2. **Blog Page Detection**: Finds blog listing pages using:
   - Links on homepage (`/blog/`, `/news/`, `/articles/`, etc.)
   - Fallback: Direct path checking if not found in HTML
3. **AI Selector Generation**: Uses Claude 3.5 Sonnet to generate CSS selectors
4. **Validation**: Tests selectors on actual articles
5. **Code Generation**: Creates ready-to-use Python scraper from template
6. **Metadata**: Saves selectors and validation results

## Generated Scraper Example

```python
from scrapers.example_scraper import get_articles

# Scrape articles
articles = get_articles("https://example.com")

# Process results
for article in articles:
    print(f"Title: {article.title}")
    print(f"URL: {article.url}")
    print(f"Author: {article.author}")
    print(f"Published: {article.published}")
    print(f"Content: {article.content[:200]}...")
```

## Article Data Structure

```python
@dataclass
class Article:
    url: str           # Article URL
    title: str         # Title
    author: str        # Author (optional)
    published: str     # Publication date (optional)
    content: str       # Full article text (optional)
```

## Advanced Features

### SPA Detection

The generator automatically detects JavaScript-rendered sites and provides clear feedback:

```
⚠️  This website appears to use JavaScript rendering (SPA/React/Vue/Angular).

The scraper generator currently works with server-rendered HTML sites only.
JavaScript-based sites require browser automation (Selenium/Playwright), which is not yet supported.

Detected framework indicators:
  - React framework detected
  - Webpack module loader detected
  - Heavy JavaScript content (script/text ratio too high)
```

### Pagination Handling

Automatically detects and uses correct pagination paths:
- Blog at root: `/page/2/`, `/page/3/`
- Blog at `/blog/`: `/blog/page/2/`, `/blog/page/3/`
- Blog at `/reviews/`: `/reviews/page/2/`, `/reviews/page/3/`

### Relative vs Absolute URLs

Handles both:
- Relative: `articles/my-post/`
- Absolute: `/articles/my-post/`
- Full URLs: `https://example.com/articles/my-post/`

## Configuration

### LLM Model

Default: `anthropic/claude-3.5-sonnet` (via OpenRouter)

To change model, edit `llm_client.py`:
```python
self.model = "anthropic/claude-3.5-sonnet"  # Change to desired model
```

Available models: https://openrouter.ai/models

### HTML Limits

- Homepage analysis: 40,000 characters
- Blog page analysis: 50,000 characters

Adjust in `llm_client.py` if needed.

## Limitations

### Supported Sites
- ✅ Server-rendered HTML (WordPress, static sites, etc.)
- ✅ Sites with standard pagination
- ✅ Public content (no authentication)

### Not Supported
- ❌ JavaScript-rendered sites (React, Vue, Angular SPAs)
- ❌ Sites requiring authentication/login
- ❌ Sites behind paywalls
- ❌ Sites with heavy anti-bot protection

## Utilities

### Test Single Scraper
```bash
python test_single_scraper.py scrapers/example_scraper.py
```

### Run All Scrapers
```bash
python run_all_scrapers.py --max-articles 5 --output results.json
```

## Troubleshooting

### No articles found
- Check if site has a `/blog/`, `/news/`, or `/articles/` section
- Try providing direct URL to blog page
- Verify site is server-rendered (not SPA)

### Low validation score
- Generator automatically retries with refinements
- Check metadata JSON file for selector details
- Site may have non-standard structure

### SPA detected
- Site requires JavaScript rendering
- Consider using Selenium/Playwright for these sites
- Or find an API endpoint if available

## Recent Improvements

- ✅ Added fallback blog page detection (checks standard paths directly)
- ✅ Increased HTML analysis limit to 40KB for better coverage
- ✅ Added intelligent SPA/framework detection
- ✅ Fixed relative URL handling (stories/ vs /stories/)
- ✅ Added `/reviews/` pattern support
- ✅ Improved error messages with actionable guidance

## License

MIT License

## Author

Developed as part of a technical assessment.
