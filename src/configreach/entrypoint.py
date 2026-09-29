from __future__ import annotations

from . import cli
from .diffing import diff_report
from .engine import scan


def main(argv: list[str] | None = None) -> int:
    # Keep the stable CLI implementation while routing scans/diffs through the
    # versioned semantic engine. This avoids duplicating command parsing/policy.
    cli.scan = scan
    cli._diff_report = diff_report
    return cli.main(argv)
