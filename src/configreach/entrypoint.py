from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import cli
from .capabilities import builtin_capability_document
from .diffing import diff_report
from .engine import scan
from .fixture_exporters import FIXTURE_FORMATS, render_fixture
from .planner import build_plan, render_plan
from .plugins import adapter_inventory
from .reproducibility import render_repro, verify_reproducibility
from .schemas import SCHEMAS, schema_registry_document, validate_document
from .workspace import render_workspace, scan_workspaces


def _plan_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="configreach plan",
        description="Build a deterministic bounded N-wise configuration test plan",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository path")
    parser.add_argument("--strength", type=int, choices=[1, 2, 3], default=2)
    parser.add_argument("--max-cases", type=int, default=64)
    parser.add_argument("--max-domain", type=int, default=12)
    parser.add_argument("--max-interactions", type=int, default=20000)
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--fixture", choices=sorted(FIXTURE_FORMATS), help="export fixture scaffolding instead of a report")
    parser.add_argument("--output")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = scan(args.path, use_cache=not args.no_cache)
        plan = build_plan(
            report,
            strength=args.strength,
            max_cases=args.max_cases,
            max_domain=args.max_domain,
            max_interactions=args.max_interactions,
        )
        text = render_fixture(plan, args.fixture) if args.fixture else render_plan(plan, args.format)
        cli._emit(text, args.output)
        return 0
    except ValueError as exc:
        sys.stderr.write(f"ConfigReach: {exc}\n")
        return 2


def _workspace_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="configreach workspace",
        description="Scan manifest-defined monorepo workspaces with independent cache boundaries",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository path")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--output")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = scan_workspaces(args.path, use_cache=not args.no_cache)
        cli._emit(render_workspace(report, args.format), args.output)
        return 0
    except ValueError as exc:
        sys.stderr.write(f"ConfigReach: {exc}\n")
        return 2


def _adapters_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="configreach adapters",
        description="Show built-in and installed adapter capabilities",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    data = builtin_capability_document()
    data.update(adapter_inventory())
    if args.format == "json":
        cli._emit(json.dumps(data, indent=2, sort_keys=True) + "\n", args.output)
        return 0

    lines = [
        f"ConfigReach adapter API v{data['adapter_api_version']}",
        f"Built-in capability schema v{data['schema_version']}",
        "",
        "Built-ins:",
    ]
    for item in data["builtins"]:
        flags = []
        for flag in ("function_scope", "finite_domains", "validators", "test_values"):
            if item.get(flag):
                flags.append(flag.replace("_", "-"))
        suffix = f" [{', '.join(flags)}]" if flags else ""
        lines.append(f"- {item['adapter_id']}: {item['ecosystem']} / {item['mode']}{suffix}")
    lines += ["", "Installed plugins:"]
    if data["plugins"]:
        for item in data["plugins"]:
            capabilities = ", ".join(item["capabilities"]) or "unspecified"
            lines.append(
                f"- {item['name']}: api={item['api_version']} parser={item['parser']} capabilities={capabilities}"
            )
    else:
        lines.append("- none")
    if data["warnings"]:
        lines += ["", "Warnings:"] + [f"- {warning}" for warning in data["warnings"]]
    cli._emit("\n".join(lines) + "\n", args.output)
    return 0


def _reproduce_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="configreach reproduce",
        description="Verify deterministic scan output across repeated uncached runs",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository path")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = verify_reproducibility(scan, args.path, runs=args.runs)
        cli._emit(render_repro(result, args.format), args.output)
        return 0 if result.reproducible else 1
    except ValueError as exc:
        sys.stderr.write(f"ConfigReach: {exc}\n")
        return 2


def _schema_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="configreach schema",
        description="Inspect and validate ConfigReach machine-readable schema compatibility",
    )
    parser.add_argument("--kind", choices=sorted(SCHEMAS), help="artifact kind when validating a file")
    parser.add_argument("--check", help="JSON artifact to validate")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    if args.check:
        if not args.kind:
            sys.stderr.write("ConfigReach: --kind is required with --check\n")
            return 2
        try:
            data = json.loads(Path(args.check).read_text(encoding="utf-8"))
            result = validate_document(args.kind, data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            sys.stderr.write(f"ConfigReach: {exc}\n")
            return 2
        payload = result.to_dict()
        if args.format == "json":
            text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        else:
            lines = [
                f"ConfigReach schema check: {'PASS' if result.compatible else 'FAIL'}",
                f"kind: {result.kind}",
                f"document version: {result.schema_version}",
                f"supported: {result.min_supported_version}..{result.current_version}",
                f"status: {result.status}",
            ]
            lines.extend(f"warning: {item}" for item in result.warnings)
            lines.extend(f"error: {item}" for item in result.errors)
            text = "\n".join(lines) + "\n"
        cli._emit(text, args.output)
        return 0 if result.compatible else 1

    data = schema_registry_document()
    if args.format == "json":
        cli._emit(json.dumps(data, indent=2, sort_keys=True) + "\n", args.output)
        return 0
    lines = ["ConfigReach schema registry"]
    for name, spec in sorted(SCHEMAS.items()):
        lines.append(
            f"- {name}: current={spec.current_version} supported={spec.min_supported_version}..{spec.current_version}"
        )
    cli._emit("\n".join(lines) + "\n", args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "plan":
        return _plan_main(args[1:])
    if args and args[0] == "workspace":
        return _workspace_main(args[1:])
    if args and args[0] == "adapters":
        return _adapters_main(args[1:])
    if args and args[0] == "reproduce":
        return _reproduce_main(args[1:])
    if args and args[0] == "schema":
        return _schema_main(args[1:])

    # Keep the stable CLI implementation while routing scans/diffs through the
    # versioned semantic engine. This avoids duplicating command parsing/policy.
    cli.scan = scan
    cli._diff_report = diff_report
    return cli.main(args)
