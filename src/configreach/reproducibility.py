from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from .models import ScanReport
from .schemas import REPRODUCIBILITY_SCHEMA_VERSION


@dataclass(frozen=True)
class ReproRun:
    run: int
    digest: str


@dataclass
class ReproResult:
    runs: list[ReproRun]
    reproducible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REPRODUCIBILITY_SCHEMA_VERSION,
            "reproducible": self.reproducible,
            "runs": [{"run": item.run, "sha256": item.digest} for item in self.runs],
        }


def canonical_report(report: ScanReport) -> bytes:
    data = report.to_dict()
    # Absolute roots are environment-specific and do not change scan semantics.
    data["root"] = "."
    summary = data.get("summary")
    if isinstance(summary, dict):
        summary.pop("scan_seconds", None)
        summary.pop("cache_hit", None)
    data.pop("scan_seconds", None)
    data.pop("cache_hit", None)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def report_digest(report: ScanReport) -> str:
    return hashlib.sha256(canonical_report(report)).hexdigest()


def verify_reproducibility(
    scan_fn: Callable[..., ScanReport],
    path: str,
    *,
    runs: int = 2,
) -> ReproResult:
    if runs < 2 or runs > 10:
        raise ValueError("runs must be between 2 and 10")
    results: list[ReproRun] = []
    for index in range(1, runs + 1):
        report = scan_fn(path, use_cache=False)
        results.append(ReproRun(index, report_digest(report)))
    reproducible = len({item.digest for item in results}) == 1
    return ReproResult(results, reproducible)


def render_repro(result: ReproResult, format_name: str = "text") -> str:
    if format_name == "json":
        return json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if format_name != "text":
        raise ValueError(f"unsupported reproducibility format: {format_name}")
    status = "PASS" if result.reproducible else "FAIL"
    lines = [f"ConfigReach reproducibility: {status}"]
    lines.extend(f"run {item.run}: {item.digest}" for item in result.runs)
    return "\n".join(lines) + "\n"
