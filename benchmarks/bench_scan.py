"""Synthetic CPU benchmark for ConfigReach.

Usage: python benchmarks/bench_scan.py [number_of_files]
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from configreach.discover import scan


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for i in range(count):
            (root / f"module_{i}.py").write_text(
                f'import os\nVALUE = os.getenv("CFG_{i:05d}", "off")\n', encoding="utf-8"
            )
        tests = root / "tests"
        tests.mkdir()
        (tests / "test_sample.py").write_text(
            'def test_sample(monkeypatch):\n    monkeypatch.setenv("CFG_00000", "on")\n', encoding="utf-8"
        )
        started = time.perf_counter()
        report = scan(root, use_cache=False)
        elapsed = time.perf_counter() - started
        print(f"files={count + 1} keys={report.total} seconds={elapsed:.3f} files_per_second={(count + 1)/elapsed:.1f}")


if __name__ == "__main__":
    main()
