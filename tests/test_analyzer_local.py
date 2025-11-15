from pathlib import Path
import sys

# Додаємо корінь репозиторію до шляху, щоб імпортувати analyzer
sys.path.append(str(Path(__file__).resolve().parents[1]))

from analyzer import SiteAnalyzer


def test_nested_index_files_are_included(tmp_path):
    root_index = tmp_path / "index.html"
    root_index.write_text("root")

    nested_dir = tmp_path / "articles"
    nested_dir.mkdir()
    nested_index = nested_dir / "index.html"
    nested_index.write_text("nested")

    article_page = tmp_path / "articles" / "story.html"
    article_page.write_text("story")

    analyzer = SiteAnalyzer(str(tmp_path), is_local=True)
    files = analyzer._find_local_html_files(max_files=5)

    assert str(root_index) not in files
    assert str(nested_index) in files
    assert str(article_page) in files
