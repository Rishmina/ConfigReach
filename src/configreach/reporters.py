from __future__ import annotations

import html
import json
from typing import Any

from . import __version__
from .models import ScanReport


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def text_report(report: ScanReport) -> str:
    lines = [
        "ConfigReach — configuration coverage",
        "=" * 39,
        f"Files scanned:              {report.files_scanned}",
        f"Test files scanned:         {report.tests_scanned}",
        f"Configuration inputs:       {report.total}",
        f"Effective inputs:           {report.effective_total}",
        f"Baseline ignored:           {report.baseline_ignored}",
        f"Covered inputs:             {report.covered}",
        f"Uncovered inputs:           {report.uncovered}",
        f"Configuration coverage:     {report.coverage * 100:.1f}%",
        f"Known-value coverage:       {_pct(report.value_coverage)}",
        f"Branch-state coverage:      {_pct(report.branch_coverage)}",
        f"Enum coverage:              {_pct(report.enum_coverage)}",
        f"Boolean coverage:           {_pct(report.boolean_coverage)}",
        f"Pairwise key coverage:      {_pct(report.combination_coverage)}",
        f"Pairwise value coverage:    {_pct(report.value_combination_coverage)}",
        f"Used but undeclared:        {report.undeclared_used}",
        f"Declared but unused:        {report.declared_unused}",
        f"Package roots:              {len(report.package_roots)}",
        f"Scan time:                  {report.scan_seconds:.3f}s{' (cache)' if report.cache_hit else ''}",
    ]
    uncovered = [x for x in report.effective_keys if not x.covered]
    if uncovered:
        lines += ["", "Uncovered configuration:"]
        for item in sorted(uncovered, key=lambda x: x.name):
            where = item.reads[0].path if item.reads else (item.declarations[0].path if item.declarations else "?")
            lines.append(f"  - {item.name} ({where})")
    severe = [f for f in report.findings if f.severity == "error"]
    if severe:
        lines += ["", "Errors:"] + [f"  - {f.rule_id} {f.message}" for f in severe]
    if report.warnings:
        lines += ["", "Scanner warnings:"] + [f"  - {w}" for w in report.warnings]
    return "\n".join(lines) + "\n"


def markdown_report(report: ScanReport) -> str:
    lines = [
        "# ConfigReach report", "",
        f"**Configuration coverage: {report.coverage * 100:.1f}%**", "",
        "| Metric | Value |", "|---|---:|",
        f"| Files scanned | {report.files_scanned} |",
        f"| Test files scanned | {report.tests_scanned} |",
        f"| Configuration inputs | {report.total} |",
        f"| Effective inputs | {report.effective_total} |",
        f"| Baseline ignored | {report.baseline_ignored} |",
        f"| Covered | {report.covered} |",
        f"| Uncovered | {report.uncovered} |",
        f"| Value coverage | {_pct(report.value_coverage)} |",
        f"| Branch-state coverage | {_pct(report.branch_coverage)} |",
        f"| Enum coverage | {_pct(report.enum_coverage)} |",
        f"| Boolean coverage | {_pct(report.boolean_coverage)} |",
        f"| Pairwise key combination coverage | {_pct(report.combination_coverage)} |",
        f"| Pairwise value-state coverage | {_pct(report.value_combination_coverage)} |",
        f"| Used but undeclared | {report.undeclared_used} |",
        f"| Declared but unused | {report.declared_unused} |",
        "", "## Configuration matrix", "",
        "| Key | Covered | Used | Declared | Value coverage | Blast radius | Categories |", "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name in sorted(report.keys):
        item = report.keys[name]
        baseline = " *(baseline)*" if item.baseline_ignored else ""
        lines.append(
            f"| `{name}`{baseline} | {'✅' if item.covered else '❌'} | {'✅' if item.used else '—'} | "
            f"{'✅' if item.declared else '—'} | {_pct(item.value_coverage)} | {item.blast_radius_files} files | "
            f"{', '.join(sorted(item.categories)) or '—'} |"
        )
    if report.findings:
        lines += ["", "## Findings", "", "| Rule | Severity | Finding |", "|---|---|---|"]
        for finding in report.findings:
            message = finding.message.replace("|", "\\|")
            lines.append(f"| `{finding.rule_id}` | {finding.severity} | {message} |")
    return "\n".join(lines) + "\n"


def json_report(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def sarif_report(report: ScanReport) -> str:
    rules = {
        "CR001": {"name": "uncovered-configuration", "shortDescription": {"text": "Configuration input is not exercised by tests"}},
        "CR002": {"name": "used-but-undeclared", "shortDescription": {"text": "Configuration is read by code but not declared"}},
        "CR003": {"name": "declared-but-unused", "shortDescription": {"text": "Configuration is declared but not read by code"}},
        "CR004": {"name": "untested-values", "shortDescription": {"text": "Known configuration values are not exercised by tests"}},
        "CR005": {"name": "sensitive-default", "shortDescription": {"text": "Sensitive-looking configuration has a non-empty default"}},
        "CR006": {"name": "inconsistent-name", "shortDescription": {"text": "Potential inconsistent configuration naming"}},
        "CR007": {"name": "production-value-untested", "shortDescription": {"text": "Production-like configuration value is not exercised"}},
        "CR008": {"name": "default-only-test-values", "shortDescription": {"text": "Explicit tests only exercise default configuration values"}},
        "CR009": {"name": "global-environment-overwrite", "shortDescription": {"text": "A test mutates the global environment and may leak configuration state"}},
    }
    results: list[dict[str, Any]] = []
    for finding in report.findings:
        result: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": {"note": "note", "warning": "warning", "error": "error"}.get(finding.severity, "warning"),
            "message": {"text": finding.message},
        }
        if finding.location:
            result["locations"] = [{"physicalLocation": {
                "artifactLocation": {"uri": finding.location.path},
                "region": {"startLine": max(1, finding.location.line)},
            }}]
        results.append(result)
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "ConfigReach", "version": __version__, "rules": [
                {"id": rid, **meta} for rid, meta in rules.items()
            ]}},
            "results": results,
        }],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def html_report(report: ScanReport) -> str:
    rows = []
    graph_cards = []
    for name in sorted(report.keys):
        item = report.keys[name]
        status = "covered" if item.covered else "uncovered"
        rows.append(
            f'<tr data-search="{html.escape(name.lower())} {html.escape(" ".join(item.categories).lower())}">'
            f'<td><code>{html.escape(name)}</code></td><td class="{status}">{"yes" if item.covered else "no"}</td>'
            f'<td>{"yes" if item.used else "no"}</td><td>{"yes" if item.declared else "no"}</td>'
            f'<td>{_pct(item.value_coverage)}</td><td>{item.blast_radius_files}</td>'
            f'<td>{html.escape(", ".join(sorted(item.categories)) or "—")}</td></tr>'
        )
        locations = []
        for loc in sorted(set(item.reads + item.branches + item.declarations + item.test_mentions)):
            locations.append(
                f'<li><a href="{html.escape(loc.path)}#L{loc.line}">{html.escape(loc.path)}:{loc.line}</a> '
                f'<span>{html.escape(loc.kind)} · {html.escape(loc.detail)}</span></li>'
            )
        graph_cards.append(
            f'<details class="node" data-search="{html.escape(name.lower())}"><summary><code>{html.escape(name)}</code> '
            f'→ {item.blast_radius_files} source file(s)</summary><ul>{"".join(locations) or "<li>No source locations</li>"}</ul></details>'
        )
    payload = html.escape(json.dumps(report.to_dict(), sort_keys=True))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ConfigReach report</title>
<style>
body{{font:15px system-ui,sans-serif;max-width:1180px;margin:40px auto;padding:0 20px;color:#1f2328}}h1{{margin-bottom:4px}}.hero{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:24px 0}}.metric{{border:1px solid #d0d7de;border-radius:10px;padding:14px}}.metric b{{font-size:24px;display:block}}input{{width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #d0d7de;border-radius:8px;margin:12px 0 18px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:8px;border-bottom:1px solid #d8dee4;text-align:left}}th{{position:sticky;top:0;background:white}}.covered{{color:#116329}}.uncovered{{color:#cf222e;font-weight:700}}code{{background:#f6f8fa;padding:2px 5px;border-radius:4px}}details{{border:1px solid #d8dee4;border-radius:8px;padding:9px 12px;margin:8px 0}}summary{{cursor:pointer}}li span{{color:#57606a}}footer{{margin:30px 0;color:#57606a}}
</style></head><body>
<h1>ConfigReach</h1><p>Deterministic configuration coverage report</p>
<div class="hero"><div class="metric"><b>{report.coverage*100:.1f}%</b>key coverage</div><div class="metric"><b>{_pct(report.value_coverage)}</b>value coverage</div><div class="metric"><b>{_pct(report.branch_coverage)}</b>branch coverage</div><div class="metric"><b>{_pct(report.boolean_coverage)}</b>boolean coverage</div><div class="metric"><b>{_pct(report.combination_coverage)}</b>key-pair coverage</div><div class="metric"><b>{_pct(report.value_combination_coverage)}</b>value-pair coverage</div><div class="metric"><b>{report.uncovered}</b>uncovered</div><div class="metric"><b>{len(report.findings)}</b>findings</div></div>
<label for="q"><b>Search configuration graph</b></label><input id="q" type="search" placeholder="Search key or category…">
<h2>Configuration matrix</h2><table><thead><tr><th>Key</th><th>Covered</th><th>Used</th><th>Declared</th><th>Value coverage</th><th>Blast radius</th><th>Categories</th></tr></thead><tbody id="matrix">{''.join(rows)}</tbody></table>
<h2>Configuration graph</h2><p>Each node links a configuration key to its detected source, declaration and test locations.</p><section id="graph">{''.join(graph_cards)}</section>
<details><summary>Embedded machine-readable report</summary><pre>{payload}</pre></details>
<footer>Generated by ConfigReach {html.escape(__version__)} · CPU-only · no network · no model required</footer>
<script>const q=document.getElementById('q');q.addEventListener('input',()=>{{const s=q.value.toLowerCase();document.querySelectorAll('[data-search]').forEach(el=>el.hidden=!el.dataset.search.includes(s));}});</script>
</body></html>'''


def render(report: ScanReport, fmt: str) -> str:
    if fmt == "text":
        return text_report(report)
    if fmt == "json":
        return json_report(report)
    if fmt == "markdown":
        return markdown_report(report)
    if fmt == "sarif":
        return sarif_report(report)
    if fmt == "html":
        return html_report(report)
    raise ValueError(f"unknown format: {fmt}")
