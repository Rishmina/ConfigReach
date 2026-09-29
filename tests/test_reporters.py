import json
from pathlib import Path

from configreach.discover import scan
from configreach.reporters import json_report, markdown_report, sarif_report


def test_report_formats(tmp_path: Path):
    (tmp_path / "app.py").write_text('import os\nx = os.getenv("MODE")\n', encoding="utf-8")
    report = scan(tmp_path)
    assert json.loads(json_report(report))["summary"]["configuration_inputs"] == 1
    assert "Configuration matrix" in markdown_report(report)
    sarif = json.loads(sarif_report(report))
    assert sarif["version"] == "2.1.0"
    assert any(r["ruleId"] == "CR001" for r in sarif["runs"][0]["results"])
