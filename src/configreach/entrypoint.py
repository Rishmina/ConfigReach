from __future__ import annotations

import argparse
import sys

from . import cli
from .diffing import diff_report
from .engine import scan
from .planner import build_plan, render_plan


def _plan_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="configreach plan",
        description="Build a deterministic bounded N-wise configuration test plan",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository path")
    parser.add_argument("--strength", type=int, choices=[1, 2, 3], default=2)
    parser.add_argument("--max-cases", type=int, default=64)
    parser.add_argument("--max-domain", type=int, default=12)
    parser.add_argument("--max-interactions", type=int, default=20000)
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--output")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = scan(args.path, use_cache=not args.no_cache)
        plan = build_plan(
            report,
            strength=args.strength,
            max_cases=args.max_cases,
            max_domain=args.max_domain,
            max_interactions=args.max_interactions,
        )
        cli._emit(render_plan(plan, args.format), args.output)
        return 0
    except ValueError as exc:
        sys.stderr.write(f"ConfigReach: {exc}\n")
        return 2


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "plan":
        return _plan_main(args[1:])

    # Keep the stable CLI implementation while routing scans/diffs through the
    # versioned semantic engine. This avoids duplicating command parsing/policy.
    cli.scan = scan
    cli._diff_report = diff_report
    return cli.main(args)
