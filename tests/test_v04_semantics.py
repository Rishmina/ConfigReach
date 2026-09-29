import subprocess
from pathlib import Path

from configreach.diffing import changed_line_ranges, diff_report
from configreach.engine import scan


def test_javascript_scope_defaults_branches_and_test_scenarios(tmp_path: Path):
    (tmp_path / "app.ts").write_text(
        "export function checkout() {\n"
        "  const mode = process.env.PAYMENT_MODE ?? 'sandbox';\n"
        "  const region = process.env.REGION;\n"
        "  if (mode === 'live') return region;\n"
        "  return 'sandbox';\n"
        "}\n"
        "export function unrelated() { return process.env.UNRELATED; }\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "app.test.ts").write_text(
        "test('live', () => {\n"
        "  process.env.PAYMENT_MODE = 'live';\n"
        "  process.env.REGION = 'eu';\n"
        "});\n",
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    mode = report.key("PAYMENT_MODE")
    assert mode is not None
    assert mode.defaults == {"sandbox"}
    assert "live" in mode.expected_values
    assert "live" in mode.tested_values
    assert any(loc.detail == "javascript:checkout" for loc in mode.reads)
    assert ("PAYMENT_MODE", "REGION") in report.pairwise_pairs
    assert ("PAYMENT_MODE", "UNRELATED") not in report.pairwise_pairs


def test_go_scope_comparisons_and_test_values(tmp_path: Path):
    (tmp_path / "main.go").write_text(
        'package main\nimport "os"\n'
        'func Run() string {\n  mode := os.Getenv("MODE")\n  region := os.Getenv("REGION")\n  if mode == "prod" { return region }\n  return "dev"\n}\n'
        'func Other() string { return os.Getenv("OTHER") }\n',
        encoding="utf-8",
    )
    (tmp_path / "main_test.go").write_text(
        'package main\nimport "testing"\nfunc TestRun(t *testing.T) {\n  t.Setenv("MODE", "prod")\n  t.Setenv("REGION", "us")\n}\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    mode = report.key("MODE")
    assert mode is not None
    assert "prod" in mode.expected_values
    assert "prod" in mode.tested_values
    assert any(loc.detail == "go:Run" for loc in mode.reads)
    assert ("MODE", "REGION") in report.pairwise_pairs
    assert ("MODE", "OTHER") not in report.pairwise_pairs


def test_spring_value_configuration_properties_and_flags(tmp_path: Path):
    (tmp_path / "PaymentConfig.java").write_text(
        'import org.springframework.beans.factory.annotation.Value;\n'
        'import org.springframework.boot.context.properties.ConfigurationProperties;\n'
        'class Service { @Value("${payment.mode:sandbox}") String mode; }\n'
        '@ConfigurationProperties(prefix="payment")\n'
        'class PaymentProperties {\n private boolean enabled = false;\n private String region = "us";\n}\n'
        'class Flags { boolean x(Client c) { return c.isEnabled("checkout-v2"); } }\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    mode = report.key("payment.mode")
    assert mode is not None and mode.used
    assert "sandbox" in mode.defaults
    enabled = report.key("payment.enabled")
    assert enabled is not None and {"true", "false"} <= enabled.expected_values
    assert report.key("checkout-v2") is not None


def test_dotnet_environment_configuration_and_feature_flags(tmp_path: Path):
    (tmp_path / "Program.cs").write_text(
        'var region = Environment.GetEnvironmentVariable("REGION");\n'
        'var mode = configuration["Payment:Mode"];\n'
        'var timeout = configuration.GetValue<int>("Payment:Timeout", 30);\n'
        'var enabled = await featureManager.IsEnabledAsync("CheckoutV2");\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert report.key("REGION").used
    assert report.key("Payment:Mode").used
    timeout = report.key("Payment:Timeout")
    assert timeout is not None and "30" in timeout.defaults
    flag = report.key("CheckoutV2")
    assert flag is not None and {"true", "false"} <= flag.expected_values


def test_json_schema_domains_and_validators(tmp_path: Path):
    (tmp_path / "config.schema.json").write_text(
        '{"type":"object","properties":{'
        '"MODE":{"type":"string","enum":["dev","prod"],"default":"dev"},'
        '"ENABLED":{"type":"boolean"},'
        '"nested":{"type":"object","properties":{"REGION":{"type":"string","pattern":"^[a-z]+$"}}}'
        '}}',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    mode = report.key("MODE")
    assert mode.expected_values == {"dev", "prod"}
    assert mode.defaults == {"dev"}
    assert "json-schema:enum" in mode.validators
    assert {"true", "false"} <= report.key("ENABLED").expected_values
    assert "json-schema:pattern=^[a-z]+$" in report.key("nested.REGION").validators
    assert report.key("properties.MODE.enum") is None


def test_terraform_finite_domain_extraction(tmp_path: Path):
    (tmp_path / "variables.tf").write_text(
        'variable "mode" {\n'
        '  type = string\n'
        '  validation {\n'
        '    condition = contains(["dev", "prod"], var.mode)\n'
        '    error_message = "bad"\n'
        '  }\n'
        '}\n'
        'variable "enabled" {\n  type = bool\n}\n',
        encoding="utf-8",
    )
    report = scan(tmp_path, use_cache=False)
    assert {"dev", "prod"} <= report.key("mode").expected_values
    assert "terraform:contains-domain" in report.key("mode").validators
    assert {"true", "false"} <= report.key("enabled").expected_values


def test_diff_uses_changed_line_slicing(tmp_path: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ConfigReach Test"], cwd=tmp_path, check=True)
    (tmp_path / "app.py").write_text(
        "import os\n"
        "A = os.getenv('UNCHANGED_KEY')\n"
        "B = os.getenv('CHANGED_KEY', 'dev')\n"
        "if B == 'prod': pass\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "app.py").write_text(
        "import os\n"
        "A = os.getenv('UNCHANGED_KEY')\n"
        "B = os.getenv('CHANGED_KEY', 'dev')\n"
        "if B == 'production': pass\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "head"], cwd=tmp_path, check=True, capture_output=True)

    ranges = changed_line_ranges(tmp_path, "HEAD~1...HEAD")
    assert ranges["app.py"] == [(4, 4)]
    text = diff_report(tmp_path, "HEAD~1...HEAD", use_cache=False)
    assert "Line-scoped configuration inputs touched: **1**" in text
    assert "`CHANGED_KEY`" in text
    # UNCHANGED_KEY exists in the repository but is not attributed to this one-line change.
    table = text.split("| Key |", 1)[1] if "| Key |" in text else text
    assert "`UNCHANGED_KEY`" not in table
