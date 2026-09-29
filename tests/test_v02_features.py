import json
from pathlib import Path

from configreach.baseline import write_baseline
from configreach.discover import scan
from configreach.reporters import html_report


def test_deployment_and_settings_sources(tmp_path: Path):
    (tmp_path / "Dockerfile").write_text("ARG BUILD_MODE=release\nENV REGION=us-east-1\n", encoding="utf-8")
    (tmp_path / "application.properties").write_text("service.timeout=30\n", encoding="utf-8")
    (tmp_path / "deploy.yml").write_text(
        "env:\n  FEATURE_X: true\n  - name: API_TOKEN\n${{ vars.RELEASE_CHANNEL }}\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.key("BUILD_MODE").declared
    assert "docker" in report.key("REGION").categories
    assert report.key("service.timeout").declared
    assert report.key("FEATURE_X").declared
    assert report.key("API_TOKEN").declared
    assert "actions-var" in report.key("RELEASE_CHANNEL").categories


def test_pydantic_settings_and_feature_flag(tmp_path: Path):
    (tmp_path / "settings.py").write_text(
        "from pydantic_settings import BaseSettings\n"
        "from pydantic import Field\n"
        "class Settings(BaseSettings):\n"
        "    payment_mode: str = Field('sandbox', validation_alias='PAYMENT_MODE')\n"
        "def enabled(client):\n"
        "    return client.is_enabled('checkout-v2')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    payment = report.key("PAYMENT_MODE")
    assert payment is not None and payment.declared
    assert "pydantic" in payment.categories
    flag = report.key("checkout-v2")
    assert flag is not None and flag.used
    assert {"true", "false"} <= flag.expected_values


def test_value_boolean_and_pairwise_coverage(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        'import os\nA=os.getenv("FEATURE_A", "false")\nB=os.getenv("MODE", "dev")\n'
        'if os.getenv("FEATURE_A", "false") == "true": pass\n'
        'if os.getenv("MODE", "dev") == "prod": pass\n',
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text(
        'def test_config(monkeypatch):\n'
        '    monkeypatch.setenv("FEATURE_A", "true")\n'
        '    monkeypatch.setenv("FEATURE_A", "false")\n'
        '    monkeypatch.setenv("MODE", "prod")\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.boolean_coverage == 1.0
    assert report.combination_coverage == 1.0
    assert report.key("MODE").value_coverage == 1.0


def test_baseline_suppresses_legacy_uncovered(tmp_path: Path):
    (tmp_path / "app.py").write_text('import os\nx=os.getenv("LEGACY_MODE")\n', encoding="utf-8")
    report = scan(tmp_path, use_cache=False)
    baseline = tmp_path / ".configreach" / "baseline.json"
    write_baseline(report, baseline)
    report2 = scan(tmp_path, use_cache=False)
    assert report2.key("LEGACY_MODE").baseline_ignored
    assert report2.effective_total == 0
    assert report2.coverage == 1.0


def test_cache_roundtrip(tmp_path: Path):
    (tmp_path / "app.py").write_text('import os\nx=os.getenv("MODE")\n', encoding="utf-8")
    first = scan(tmp_path, use_cache=True)
    second = scan(tmp_path, use_cache=True)
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.key("MODE") is not None


def test_html_report_is_searchable(tmp_path: Path):
    (tmp_path / "app.py").write_text('import os\nx=os.getenv("MODE")\n', encoding="utf-8")
    report = scan(tmp_path, use_cache=False)
    html = html_report(report)
    assert "Search configuration graph" in html
    assert 'id="graph"' in html
    assert "MODE" in html


def test_sensitive_default_is_error(tmp_path: Path):
    (tmp_path / ".env.example").write_text("API_TOKEN=hardcoded\n", encoding="utf-8")
    report = scan(tmp_path, use_cache=False)
    assert any(f.rule_id == "CR005" and f.severity == "error" for f in report.findings)
