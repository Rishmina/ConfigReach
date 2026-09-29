import subprocess
from pathlib import Path

from configreach.cli import _diff_report
from configreach.discover import scan


def test_literal_enum_domains_and_branch_provenance(tmp_path: Path):
    (tmp_path / "settings.py").write_text(
        "from enum import Enum\n"
        "from typing import Literal\n"
        "from pydantic_settings import BaseSettings\n"
        "class Region(str, Enum):\n"
        "    US = 'us'\n"
        "    EU = 'eu'\n"
        "class Settings(BaseSettings):\n"
        "    MODE: Literal['sandbox', 'live'] = 'sandbox'\n"
        "    REGION: Region = Region.US\n"
        "    ENABLED: bool = False\n"
        "import os\n"
        "def charge():\n"
        "    mode = os.getenv('PAYMENT_MODE', 'sandbox')\n"
        "    if mode == 'live':\n"
        "        return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.key("MODE").expected_values == {"sandbox", "live"}
    assert report.key("REGION").expected_values == {"us", "eu"}
    assert {"true", "false"} <= report.key("ENABLED").expected_values
    payment = report.key("PAYMENT_MODE")
    assert payment.functions == {"charge"}
    assert payment.branches and payment.branches[0].kind == "branch"


def test_value_pair_coverage_uses_test_scenarios(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "import os\n"
        "def run():\n"
        "    a = os.getenv('FEATURE_A', 'false')\n"
        "    b = os.getenv('MODE', 'x')\n"
        "    if a == 'true': pass\n"
        "    if a == 'false': pass\n"
        "    if b == 'x': pass\n"
        "    if b == 'y': pass\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text(
        "def test_one(monkeypatch):\n"
        "    monkeypatch.setenv('FEATURE_A', 'true')\n"
        "    monkeypatch.setenv('MODE', 'x')\n"
        "def test_two(monkeypatch):\n"
        "    monkeypatch.setenv('FEATURE_A', 'false')\n"
        "    monkeypatch.setenv('MODE', 'y')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.pairwise_pairs == {("FEATURE_A", "MODE")}
    assert len(report.expected_value_pairs) == 4
    assert len(report.covered_value_pairs) == 2
    assert report.value_combination_coverage == 0.5


def test_function_scope_avoids_false_interaction_pairs(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "import os\n"
        "def first():\n"
        "    return os.getenv('A') + os.getenv('B')\n"
        "def second():\n"
        "    return os.getenv('C')\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.pairwise_pairs == {("A", "B")}
    assert "app.py::first" in report.dependency_scopes
    assert "app.py::second" in report.dependency_scopes


def test_default_only_and_global_environment_findings(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "import os\n"
        "mode=os.getenv('MODE', 'sandbox')\n"
        "if mode == 'live': pass\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text(
        "import os\n"
        "def test_default(monkeypatch):\n"
        "    monkeypatch.setenv('MODE', 'sandbox')\n"
        "    os.environ.clear()\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    rules = {finding.rule_id for finding in report.findings}
    assert "CR008" in rules
    assert "CR009" in rules


def test_sensitive_defaults_in_structured_config_are_flagged(tmp_path: Path):
    (tmp_path / "settings.json").write_text('{"API_TOKEN":"hardcoded"}', encoding="utf-8")
    report = scan(tmp_path, use_cache=False)
    assert any(f.rule_id == "CR005" for f in report.findings)


def test_diff_identifies_new_untested_configuration(tmp_path: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ConfigReach Test"], cwd=tmp_path, check=True)
    (tmp_path / "app.py").write_text("def answer(): return 42\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "app.py").write_text(
        "import os\n"
        "def answer():\n"
        "    mode=os.getenv('NEW_MODE', 'sandbox')\n"
        "    return 43 if mode == 'live' else 42\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "head"], cwd=tmp_path, check=True, capture_output=True)
    text = _diff_report(tmp_path, "HEAD~1...HEAD", use_cache=False)
    assert "New configuration inputs: **1**" in text
    assert "Newly introduced untested inputs: **1**" in text
    assert "`NEW_MODE` | NEW | ❌ untested" in text
