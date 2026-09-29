from __future__ import annotations

import json
from pathlib import Path

from .models import ScanReport


BASELINE_SCHEMA = 1


def baseline_path(root: Path, configured: str) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else root / path


def read_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(data, list):
        return {str(x) for x in data}
    if isinstance(data, dict):
        return {str(x) for x in data.get("keys", [])}
    return set()


def apply_baseline(report: ScanReport, path: Path) -> None:
    names = read_baseline(path)
    for name in names:
        item = report.keys.get(name)
        if item is not None:
            item.baseline_ignored = True


def write_baseline(report: ScanReport, path: Path, *, uncovered_only: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if uncovered_only:
        names = sorted(item.name for item in report.keys.values() if not item.covered)
    else:
        names = sorted(report.keys)
    payload = {
        "schema_version": BASELINE_SCHEMA,
        "description": "ConfigReach legacy baseline. Matching keys are excluded from CI gating until removed.",
        "keys": names,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
