"""Deterministic synthetic performance budget for the full ConfigReach engine.

The default budget is intentionally conservative so normal GitHub-hosted CPU noise does
not create flaky failures. It is meant to catch order-of-magnitude regressions, not to
serve as a microbenchmark leaderboard.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from configreach.engine import scan


def _write_source(root: Path, index: int) -> None:
    key = f"CFG_{index:05d}"
    kind = index % 5
    if kind == 0:
        (root / f"module_{index}.py").write_text(
            f'import os\nVALUE = os.getenv("{key}", "off")\n', encoding="utf-8"
        )
    elif kind == 1:
        (root / f"module_{index}.ts").write_text(
            f'export const value = process.env.{key} ?? "off";\n', encoding="utf-8"
        )
    elif kind == 2:
        (root / f"module_{index}.go").write_text(
            f'package sample\nimport "os"\nfunc value{index}() string {{ return os.Getenv("{key}") }}\n',
            encoding="utf-8",
        )
    elif kind == 3:
        (root / f"Module{index}.java").write_text(
            f'class Module{index} {{ String value() {{ return System.getenv("{key}"); }} }}\n',
            encoding="utf-8",
        )
    else:
        (root / f"Module{index}.cs").write_text(
            f'using System;\nclass Module{index} {{ string Value() => Environment.GetEnvironmentVariable("{key}"); }}\n',
            encoding="utf-8",
        )


def run_budget(files: int, min_files_per_second: float, max_seconds: float | None) -> dict[str, object]:
    if files < 10:
        raise ValueError("files must be at least 10")
    if min_files_per_second <= 0:
        raise ValueError("min-files-per-second must be positive")
    if max_seconds is not None and max_seconds <= 0:
        raise ValueError("max-seconds must be positive")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for index in range(files):
            _write_source(root, index)
        tests = root / "tests"
        tests.mkdir()
        (tests / "test_config.py").write_text(
            'def test_config(monkeypatch):\n    monkeypatch.setenv("CFG_00000", "on")\n',
            encoding="utf-8",
        )

        started = time.perf_counter()
        report = scan(root, use_cache=False)
        elapsed = time.perf_counter() - started

    scanned = report.files_scanned
    rate = scanned / elapsed if elapsed else float("inf")
    passes_rate = rate >= min_files_per_second
    passes_time = max_seconds is None or elapsed <= max_seconds
    return {
        "schema_version": 1,
        "synthetic_source_files": files,
        "files_scanned": scanned,
        "configuration_inputs": report.total,
        "seconds": round(elapsed, 6),
        "files_per_second": round(rate, 2),
        "budget": {
            "min_files_per_second": min_files_per_second,
            "max_seconds": max_seconds,
        },
        "passed": bool(passes_rate and passes_time),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ConfigReach synthetic polyglot performance budget")
    parser.add_argument("--files", type=int, default=800)
    parser.add_argument("--min-files-per-second", type=float, default=150.0)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        result = run_budget(args.files, args.min_files_per_second, args.max_seconds)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
