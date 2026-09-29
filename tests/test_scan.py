from pathlib import Path

from configreach.discover import scan


def test_python_env_and_test_coverage(tmp_path: Path):
    (tmp_path / ".env.example").write_text("PAYMENT_MODE=sandbox\nAPI_TOKEN=\n", encoding="utf-8")
    (tmp_path / "app.py").write_text(
        'import os\nMODE = os.getenv("PAYMENT_MODE", "sandbox")\nTOKEN = os.environ["API_TOKEN"]\n',
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text(
        'def test_live(monkeypatch):\n    monkeypatch.setenv("PAYMENT_MODE", "live")\n',
        encoding="utf-8",
    )

    report = scan(tmp_path)
    assert report.total == 2
    assert report.key("PAYMENT_MODE").covered is True
    assert report.key("API_TOKEN").covered is False
    assert "live" in report.key("PAYMENT_MODE").tested_values
    assert report.key("API_TOKEN").to_dict()["defaults"] in ([], ["<redacted>"])


def test_generic_language_detection(tmp_path: Path):
    (tmp_path / "index.ts").write_text('const x = process.env.FEATURE_ALPHA;\n', encoding="utf-8")
    (tmp_path / "main.go").write_text('package main\n// x\nvar x = os.Getenv("GO_MODE")\n', encoding="utf-8")
    report = scan(tmp_path)
    assert report.key("FEATURE_ALPHA").used
    assert report.key("GO_MODE").used


def test_json_settings_are_declared(tmp_path: Path):
    (tmp_path / "settings.json").write_text('{"service": {"timeout": 10}}', encoding="utf-8")
    report = scan(tmp_path)
    item = report.key("service.timeout")
    assert item is not None
    assert item.declared
    assert "settings" in item.categories
