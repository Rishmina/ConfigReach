from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import ScanReport


CACHE_SCHEMA = 1


def repository_fingerprint(root: Path, files: list[Path], config_bytes: bytes = b"") -> str:
    digest = hashlib.sha256()
    digest.update(config_bytes)
    for path in sorted(files, key=lambda p: p.as_posix()):
        rel = path.relative_to(root).as_posix()
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(rel.encode())
        digest.update(str(stat.st_size).encode())
        digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def cache_file(root: Path) -> Path:
    return root / ".configreach" / "cache" / "scan-v2.json"


def load_cache(root: Path, fingerprint: str) -> ScanReport | None:
    path = cache_file(root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("cache_schema") != CACHE_SCHEMA or data.get("fingerprint") != fingerprint:
        return None
    try:
        report = ScanReport.from_dict(data["report"])
    except (KeyError, TypeError, ValueError):
        return None
    report.cache_hit = True
    report.root = str(root)
    return report


def save_cache(root: Path, fingerprint: str, report: ScanReport) -> None:
    path = cache_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cache_schema": CACHE_SCHEMA, "fingerprint": fingerprint, "report": report.to_dict()}
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
