from __future__ import annotations

from pathlib import Path

from configreach.engine import scan
from configreach.fixture_exporters import render_fixture
from configreach.planner import PlanCase, TestPlan as ConfigReachTestPlan
from configreach.workspace import detect_workspaces, scan_workspaces


def _write_workspace(root: Path, name: str, key: str) -> Path:
    path = root / name
    (path / "tests").mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    (path / "app.py").write_text(
        f'import os\nVALUE = os.getenv("{key}", "off")\n', encoding="utf-8"
    )
    (path / "tests" / "test_app.py").write_text(
        f'def test_config(monkeypatch):\n    monkeypatch.setenv("{key}", "on")\n', encoding="utf-8"
    )
    return path


def test_workspace_detection_and_independent_cache_invalidation(tmp_path: Path) -> None:
    left = _write_workspace(tmp_path, "alpha", "ALPHA_MODE")
    _write_workspace(tmp_path, "beta", "BETA_MODE")

    roots = [path.name for path in detect_workspaces(tmp_path)]
    assert roots == ["alpha", "beta"]

    first = scan_workspaces(tmp_path, use_cache=True)
    assert len(first.workspaces) == 2
    assert first.cache_hits == 0

    second = scan_workspaces(tmp_path, use_cache=True)
    assert second.cache_hits == 2

    (left / "app.py").write_text(
        'import os\nVALUE = os.getenv("ALPHA_MODE", "off")\nEXTRA = os.getenv("ALPHA_EXTRA", "x")\n',
        encoding="utf-8",
    )
    third = scan_workspaces(tmp_path, use_cache=True)
    states = {item.path: item.cache_hit for item in third.workspaces}
    assert states["alpha"] is False
    assert states["beta"] is True


def _sample_plan() -> ConfigReachTestPlan:
    return ConfigReachTestPlan(
        strength=2,
        cases=[
            PlanCase(
                "CRP001",
                "app.py::handle",
                (("PAYMENT_MODE", "live"), ("REGION", "eu")),
                ("PAYMENT_MODE=live & REGION=eu",),
            )
        ],
        missing_values={"PAYMENT_MODE": ["live"]},
        interactions_total=4,
        interactions_already_covered=2,
        interactions_planned=1,
        interactions_remaining=1,
        scopes_considered=1,
        warnings=[],
    )


def test_fixture_exporters_are_deterministic() -> None:
    plan = _sample_plan()
    pytest_text = render_fixture(plan, "pytest")
    jest_text = render_fixture(plan, "jest")
    go_text = render_fixture(plan, "go")
    shell_text = render_fixture(plan, "shell")

    assert "configreach_env" in pytest_text
    assert '"PAYMENT_MODE": "live"' in pytest_text
    assert "configReachCases" in jest_text
    assert "package configreachfixtures" in go_text
    assert "export PAYMENT_MODE='live'" in shell_text
    assert render_fixture(plan, "pytest") == pytest_text


def test_zod_domains_and_validators(tmp_path: Path) -> None:
    (tmp_path / "settings.ts").write_text(
        'const schema = z.object({\n'
        '  PAYMENT_MODE: z.enum(["sandbox", "live"]),\n'
        '  ENABLE_ASYNC: z.boolean(),\n'
        '  RETRIES: z.number().min(1).max(5),\n'
        '});\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.keys["PAYMENT_MODE"].expected_values == {"sandbox", "live"}
    assert "zod:enum" in report.keys["PAYMENT_MODE"].validators
    assert report.keys["ENABLE_ASYNC"].expected_values >= {"true", "false"}
    assert "zod:min=1" in report.keys["RETRIES"].validators
    assert "zod:max=5" in report.keys["RETRIES"].validators


def test_extended_json_schema_domains(tmp_path: Path) -> None:
    (tmp_path / "config.schema.json").write_text(
        '{"properties":{"REGION":{"oneOf":[{"const":"in"},{"enum":["eu","us"]}],"format":"hostname"}}}',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.keys["REGION"].expected_values == {"in", "eu", "us"}
    assert "json-schema:oneOf-finite-domain" in report.keys["REGION"].validators
    assert "json-schema:format=hostname" in report.keys["REGION"].validators


def test_java_and_terraform_validator_provenance(tmp_path: Path) -> None:
    (tmp_path / "PaymentConfig.java").write_text(
        '@Min(1)\n@Max(10)\n@Value("${payment.retries:3}")\nprivate int retries;\n',
        encoding="utf-8",
    )
    (tmp_path / "variables.tf").write_text(
        'variable "replicas" {\n'
        '  type = number\n'
        '  validation {\n'
        '    condition = var.replicas >= 1 && var.replicas <= 20\n'
        '    error_message = "range"\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    java = report.keys["payment.retries"]
    assert "java:Min=1" in java.validators
    assert "java:Max=10" in java.validators
    terraform = report.keys["replicas"]
    assert "terraform:ge=1" in terraform.validators
    assert "terraform:le=20" in terraform.validators
