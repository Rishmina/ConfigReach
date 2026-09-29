"""Build ConfigReach twice and verify reproducible wheel/sdist artifacts.

This is a release-development tool. It is not imported by the ConfigReach runtime and
therefore does not add a runtime dependency.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from configreach.release import (
    build_release_manifest,
    compare_release_manifests,
    normalize_sdist,
)


def _clean_generated(root: Path) -> None:
    shutil.rmtree(root / "build", ignore_errors=True)
    for path in (root / "src").glob("*.egg-info"):
        shutil.rmtree(path, ignore_errors=True)


def _build(root: Path, output: Path, env: dict[str, str]) -> None:
    _clean_generated(root)
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--sdist",
            "--wheel",
            "--outdir",
            str(output),
            str(root),
        ],
        cwd=root,
        env=env,
        check=True,
    )
    epoch = int(env["SOURCE_DATE_EPOCH"])
    for sdist in sorted(output.glob("*.tar.gz"), key=lambda item: item.name):
        normalize_sdist(sdist, epoch)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify reproducible ConfigReach release artifacts")
    parser.add_argument("--source-date-epoch", default="1700000000")
    parser.add_argument("--output", default="release-repro.json")
    parser.add_argument("--artifacts-dir", default="dist")
    args = parser.parse_args()

    root = Path.cwd().resolve()
    env = os.environ.copy()
    env.update(
        {
            "SOURCE_DATE_EPOCH": str(args.source_date_epoch),
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
        }
    )

    with tempfile.TemporaryDirectory(prefix="configreach-release-") as tmp:
        temporary = Path(tmp)
        first_dir = temporary / "first"
        second_dir = temporary / "second"
        _build(root, first_dir, env)
        _build(root, second_dir, env)

        first = build_release_manifest(first_dir)
        second = build_release_manifest(second_dir)
        comparison = compare_release_manifests(first, second)
        payload = comparison.to_dict()
        payload["source_date_epoch"] = str(args.source_date_epoch)
        Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        artifacts_dir = Path(args.artifacts_dir)
        shutil.rmtree(artifacts_dir, ignore_errors=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        for artifact in sorted(first_dir.iterdir(), key=lambda item: item.name):
            if artifact.is_file():
                shutil.copy2(artifact, artifacts_dir / artifact.name)

    _clean_generated(root)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if comparison.exact_reproducible:
        return 0
    if comparison.content_reproducible:
        print("Release contents match, but container bytes differ.", file=sys.stderr)
    else:
        print("Release artifact contents differ.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
