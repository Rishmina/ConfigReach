from pathlib import Path

from configreach.cli import main


def test_cli_html_and_baseline(tmp_path: Path):
    (tmp_path / "app.py").write_text('import os\nx=os.getenv("MODE")\n', encoding="utf-8")
    html = tmp_path / "report.html"
    assert main(["scan", str(tmp_path), "--format", "html", "--output", str(html), "--no-cache"]) == 0
    assert "Search configuration graph" in html.read_text(encoding="utf-8")
    assert main(["baseline", "create", str(tmp_path)]) == 0
    assert (tmp_path / ".configreach" / "baseline.json").exists()


def test_fail_on_policy(tmp_path: Path):
    (tmp_path / "app.py").write_text('import os\nx=os.getenv("UNTESTED")\n', encoding="utf-8")
    assert main(["scan", str(tmp_path), "--fail-on", "uncovered", "--no-cache"]) == 2
