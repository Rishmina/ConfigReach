from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def trace_python(command: list[str], root: Path, output: Path) -> int:
    """Run supported Python commands inside ConfigReach's trace wrapper."""
    if not command:
        raise ValueError("trace requires a Python command after --")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    env = os.environ.copy()
    env["CONFIGREACH_TRACE_OUT"] = str(output)
    completed = subprocess.run(
        [sys.executable, "-m", "configreach._trace_exec", *command],
        cwd=root,
        env=env,
        check=False,
    )
    return completed.returncode


def summarize_trace(path: Path) -> tuple[int, int]:
    keys: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    if not path.exists():
        return 0, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            key, fp = item["key"], item["fingerprint"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        keys.add(str(key))
        pairs.add((str(key), str(fp)))
    return len(keys), len(pairs)
