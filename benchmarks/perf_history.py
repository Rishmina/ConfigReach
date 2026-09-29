"""Wrap a performance-budget result with CI provenance for retained history artifacts."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a ConfigReach performance history record")
    parser.add_argument("input", help="perf_budget.py JSON output")
    parser.add_argument("--output", default="performance-history.json")
    args = parser.parse_args()

    result = json.loads(Path(args.input).read_text(encoding="utf-8"))
    record = {
        "schema_version": 1,
        "commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_number": os.environ.get("GITHUB_RUN_NUMBER"),
        "runner_os": os.environ.get("RUNNER_OS"),
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "platform": sys.platform,
        "result": result,
    }
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if bool(result.get("passed")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
