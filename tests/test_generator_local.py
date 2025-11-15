from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from generator import ScraperGenerator


def _create_local_site(tmp_path: Path) -> Path:
    site_dir = tmp_path / "newsroom-hub"
    site_dir.mkdir()

    (site_dir / "index.html").write_text("root", encoding="utf-8")

    nested = site_dir / "articles" / "breaking"
    nested.mkdir(parents=True)
    (nested / "index.html").write_text("nested", encoding="utf-8")

    article = site_dir / "articles" / "story.html"
    article.write_text("story", encoding="utf-8")

    return site_dir


def test_local_scraper_includes_nested_indexes(tmp_path):
    site_dir = _create_local_site(tmp_path)

    generator = object.__new__(ScraperGenerator)
    code = generator._generate_local_scraper_code(str(site_dir), selectors={})

    namespace = {}
    exec(code, namespace)

    scraper_cls = next(
        value for key, value in namespace.items() if key.endswith("LocalScraper")
    )
    scraper = scraper_cls(site_dir=str(site_dir))

    html_files = scraper.find_html_files()

    assert site_dir / "index.html" not in html_files
    assert site_dir / "articles" / "breaking" / "index.html" in html_files
    assert site_dir / "articles" / "story.html" in html_files
