from __future__ import annotations

import json
from typing import Any

from .models import ScanReport


def text_report(report: ScanReport) -> str:
    pct = report.coverage * 100
    lines = [
        "ConfigReach — configuration coverage",
        "=" * 39,
        f"Files scanned:          {report.files_scanned}",
        f"Test files scanned:     {report.tests_scanned}",
        f"Configuration inputs:   {report.total}",
        f"Covered inputs:         {report.covered}",
        f"Uncovered inputs:       {report.uncovered}",
        f"Configuration coverage: {pct:.1f}%",
        f"Used but undeclared:    {report.undeclared_used}",
        f"Declared but unused:    {report.declared_unused}",
    ]
    uncovered = [x for x in report.keys.values() if not x.covered]
    if uncovered:
        lines += ["", "Uncovered configuration:"]
        for item in sorted(uncovered, key=lambda x: x.name):
            where = item.reads[0].path if item.reads else (item.declarations[0].path if item.declarations else "?")
            lines.append(f"  - {item.name} ({where})")
    return "\n".join(lines) + "\n"


def markdown_report(report: ScanReport) -> str:
    lines = [
        "# ConfigReach report", "",
        f"**Configuration coverage: {report.coverage * 100:.1f}%**", "",
        "| Metric | Value |", "|---|---:|",
        f"| Files scanned | {report.files_scanned} |",
        f"| Test files scanned | {report.tests_scanned} |",
        f"| Configuration inputs | {report.total} |",
        f"| Covered | {report.covered} |",
        f"| Uncovered | {report.uncovered} |",
        f"| Used but undeclared | {report.undeclared_used} |",
        f"| Declared but unused | {report.declared_unused} |",
        "", "## Configuration matrix", "",
        "| Key | Covered | Used | Declared | Categories |", "|---|---:|---:|---:|---|",
    ]
    for name in sorted(report.keys):
        item = report.keys[name]
        lines.append(
            f"| `{name}` | {'✅' if item.covered else '❌'} | {'✅' if item.used else '—'} | "
            f"{'✅' if item.declared else '—'} | {', '.join(sorted(item.categories)) or '—'} |"
        )
    return "\n".join(lines) + "\n"


def json_report(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def sarif_report(report: ScanReport) -> str:
    rules = {
        "CR001": {"name": "uncovered-configuration", "shortDescription": {"text": "Configuration input is not exercised by tests"}},
        "CR002": {"name": "used-but-undeclared", "shortDescription": {"text": "Configuration is read by code but not declared"}},
        "CR003": {"name": "declared-but-unused", "shortDescription": {"text": "Configuration is declared but not read by code"}},
    }
    results: list[dict[str, Any]] = []
    for item in report.keys.values():
        findings: list[tuple[str, str]] = []
        if not item.covered:
            findings.append(("CR001", f"{item.name} is not referenced by the detected test suite"))
        if item.used and not item.declared:
            findings.append(("CR002", f"{item.name} is read by application code but no declaration was detected"))
        if item.declared and not item.used:
            findings.append(("CR003", f"{item.name} is declared but no application read was detected"))
        loc = item.reads or item.declarations or item.test_mentions
        for rule_id, message in findings:
            result: dict[str, Any] = {"ruleId": rule_id, "level": "warning", "message": {"text": message}}
            if loc:
                result["locations"] = [{"physicalLocation": {
                    "artifactLocation": {"uri": loc[0].path},
                    "region": {"startLine": max(1, loc[0].line)},
                }}]
            results.append(result)
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "ConfigReach", "version": "0.1.0", "rules": [
                {"id": rid, **meta} for rid, meta in rules.items()
            ]}},
            "results": results,
        }],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render(report: ScanReport, fmt: str) -> str:
    if fmt == "text":
        return text_report(report)
    if fmt == "json":
        return json_report(report)
    if fmt == "markdown":
        return markdown_report(report)
    if fmt == "sarif":
        return sarif_report(report)
    raise ValueError(f"unknown format: {fmt}")
