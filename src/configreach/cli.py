from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import load_settings
from .discover import scan
from .models import ConfigKey
from .reporters import render
from .tracer import summarize_trace, trace_python


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", default=".", help="repository path")
    parser.add_argument("--format", choices=["text", "json", "markdown", "sarif"], default="text")
    parser.add_argument("--output", help="write output to a file")


def _emit(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _status(report, fail_under: float | None) -> int:
    threshold = fail_under
    if threshold is None:
        threshold = load_settings(Path(report.root)).fail_under
    if threshold is not None and report.coverage * 100 < threshold:
        return 2
    return 0


def _explain(item: ConfigKey) -> str:
    data = item.to_dict()
    lines = [
        f"{item.name}", "=" * len(item.name),
        f"Covered:  {'yes' if item.covered else 'no'}",
        f"Used:     {'yes' if item.used else 'no'}",
        f"Declared: {'yes' if item.declared else 'no'}",
        f"Sensitive:{' yes' if data['sensitive'] else ' no'}",
        f"Categories: {', '.join(data['categories']) or '—'}",
        f"Languages:  {', '.join(data['languages']) or '—'}",
    ]
    for heading, field in [("Reads", item.reads), ("Declarations", item.declarations), ("Tests", item.test_mentions)]:
        lines += ["", heading + ":"]
        lines += [f"  {loc.path}:{loc.line} ({loc.detail or loc.kind})" for loc in field] or ["  —"]
    if data["expected_values"]:
        lines += ["", "Expected values: " + ", ".join(data["expected_values"])]
        lines += ["Tested values:   " + (", ".join(data["tested_values"]) or "—")]
    return "\n".join(lines) + "\n"


def _matrix(report) -> str:
    lines = ["KEY\tCOVERED\tUSED\tDECLARED\tCATEGORIES"]
    for name in sorted(report.keys):
        item = report.keys[name]
        lines.append(
            f"{name}\t{'yes' if item.covered else 'no'}\t{'yes' if item.used else 'no'}\t"
            f"{'yes' if item.declared else 'no'}\t{','.join(sorted(item.categories))}"
        )
    return "\n".join(lines) + "\n"


def _changed_paths(root: Path, rev_range: str) -> set[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", rev_range], cwd=root, capture_output=True, text=True, check=False
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return {line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()}


def _diff_report(root: Path, rev_range: str) -> str:
    report = scan(root)
    changed = _changed_paths(root, rev_range)
    impacted = report.keys_for_paths(changed)
    lines = [
        f"ConfigReach diff: {rev_range}",
        f"Changed files: {len(changed)}",
        f"Configuration inputs touched: {len(impacted)}",
        "",
    ]
    if not impacted:
        lines.append("No configuration inputs detected in changed files.")
    for item in impacted:
        lines.append(f"{'✓' if item.covered else '!'} {item.name} — {'covered' if item.covered else 'UNTESTED'}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="configreach", description="Configuration coverage for your test suite")
    parser.add_argument("--version", action="version", version=f"ConfigReach {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "coverage", "export"):
        p = sub.add_parser(name)
        _add_common(p)
        p.add_argument("--fail-under", type=float, help="exit non-zero below this coverage percentage")
    p = sub.add_parser("explain")
    p.add_argument("key")
    p.add_argument("path", nargs="?", default=".")
    p = sub.add_parser("matrix")
    p.add_argument("path", nargs="?", default=".")
    p = sub.add_parser("diff")
    p.add_argument("revision_range", help="for example origin/main...HEAD")
    p.add_argument("path", nargs="?", default=".")
    p = sub.add_parser("doctor")
    p.add_argument("path", nargs="?", default=".")
    p = sub.add_parser("init")
    p.add_argument("path", nargs="?", default=".")
    p = sub.add_parser("trace", help="trace Python environment reads while running a command")
    p.add_argument("--path", default=".")
    p.add_argument("--output", default=".configreach/trace.jsonl")
    p.add_argument("remainder", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"scan", "coverage", "export"}:
        report = scan(args.path)
        _emit(render(report, args.format), args.output)
        return _status(report, args.fail_under)
    if args.command == "explain":
        report = scan(args.path)
        item = report.key(args.key)
        if item is None:
            sys.stderr.write(f"ConfigReach: unknown configuration key: {args.key}\n")
            return 1
        sys.stdout.write(_explain(item))
        return 0
    if args.command == "matrix":
        sys.stdout.write(_matrix(scan(args.path)))
        return 0
    if args.command == "diff":
        root = Path(args.path).resolve()
        try:
            sys.stdout.write(_diff_report(root, args.revision_range))
            return 0
        except RuntimeError as exc:
            sys.stderr.write(f"ConfigReach: {exc}\n")
            return 2
    if args.command == "doctor":
        root = Path(args.path).resolve()
        report = scan(root)
        checks = [
            (root.exists(), "repository path exists"),
            ((root / ".git").exists(), "git metadata present"),
            (report.files_scanned > 0, "supported source/config files found"),
            (report.tests_scanned > 0, "test files found"),
        ]
        for ok, message in checks:
            print(f"{'✓' if ok else '!'} {message}")
        print("✓ deterministic engine; no network/API/model required")
        return 0 if checks[0][0] and checks[2][0] else 1
    if args.command == "init":
        root = Path(args.path).resolve()
        target = root / "configreach.toml"
        if target.exists():
            sys.stderr.write("ConfigReach: configreach.toml already exists\n")
            return 1
        target.write_text(
            "[configreach]\nfail_under = 0\nignore = [\"vendor/**\", \"generated/**\"]\n\n"
            "# test_patterns = [\"tests/**\", \"**/test_*.py\"]\n",
            encoding="utf-8",
        )
        print(f"Created {target}")
        return 0
    if args.command == "trace":
        command = list(args.remainder)
        if command and command[0] == "--":
            command = command[1:]
        root = Path(args.path).resolve()
        output = (root / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
        try:
            code = trace_python(command, root, output)
        except ValueError as exc:
            sys.stderr.write(f"ConfigReach: {exc}\n")
            return 2
        keys, pairs = summarize_trace(output)
        print(f"Trace: {keys} configuration keys, {pairs} distinct value fingerprints")
        print(f"Trace file: {output}")
        return code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
