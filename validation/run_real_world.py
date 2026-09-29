from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from configreach.engine import scan


def _git(*args: str, cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _clone_pinned(repo: str, commit: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", str(destination))
    _git("remote", "add", "origin", f"https://github.com/{repo}.git", cwd=destination)
    _git("fetch", "-q", "--depth=1", "origin", commit, cwd=destination)
    _git("checkout", "-q", "--detach", "FETCH_HEAD", cwd=destination)
    resolved = _git("rev-parse", "HEAD", cwd=destination)
    if resolved != commit:
        raise RuntimeError(f"{repo}: resolved {resolved}, expected {commit}")


def _review_map(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["repo"]: item for item in data.get("reviews", [])}


def _project_result(project: dict, work: Path, review: dict | None) -> dict:
    repo = project["repo"]
    commit = project["commit"]
    target = work / repo.replace("/", "__")
    clone_started = time.perf_counter()
    _clone_pinned(repo, commit, target)
    clone_seconds = time.perf_counter() - clone_started

    started = time.perf_counter()
    report = scan(target, use_cache=False)
    wall_seconds = time.perf_counter() - started
    categories = Counter(category for key in report.effective_keys for category in key.categories)
    findings = Counter(item.rule_id for item in report.findings)

    review = review or {}
    false_positives = list(review.get("false_positives", []))
    false_negatives = list(review.get("false_negatives", []))
    return {
        "repo": repo,
        "ecosystem": project.get("ecosystem", ""),
        "commit": commit,
        "configuration_inputs": report.effective_total,
        "covered_inputs": report.covered,
        "uncovered_inputs": report.uncovered,
        "configuration_coverage": round(report.coverage, 6),
        "files_scanned": report.files_scanned,
        "tests_scanned": report.tests_scanned,
        "runtime_seconds": round(wall_seconds, 6),
        "engine_runtime_seconds": round(report.scan_seconds, 6),
        "clone_seconds": round(clone_seconds, 6),
        "category_counts": dict(sorted(categories.items())),
        "finding_counts": dict(sorted(findings.items())),
        "warnings": list(report.warnings),
        "manual_review": {
            "scope": review.get("scope", "not-yet-reviewed"),
            "false_positive_count": len(false_positives),
            "false_negative_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        },
    }


def _markdown(data: dict) -> str:
    rows = [
        "# ConfigReach real-world validation",
        "",
        "Static scans of pinned upstream commits. Target projects are not executed and their dependencies are not installed.",
        "Runtime is wall-clock scan time on the recorded runner and is therefore performance evidence, not a cross-machine guarantee.",
        "Manual false-positive/false-negative entries are targeted spot checks, not exhaustive repository-wide error rates; measured accuracy comes from the hand-labelled corpus.",
        "",
        "| Project | Ecosystem | Configs | Covered | Coverage | Runtime | Reviewed FP | Reviewed FN |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in data["projects"]:
        review = item["manual_review"]
        rows.append(
            f"| {item['repo']} | {item['ecosystem']} | {item['configuration_inputs']} | "
            f"{item['covered_inputs']} | {item['configuration_coverage'] * 100:.1f}% | "
            f"{item['runtime_seconds']:.3f}s | {review['false_positive_count']} | {review['false_negative_count']} |"
        )
    totals = data["summary"]
    rows += [
        "",
        "## Aggregate",
        "",
        f"- Projects scanned: **{totals['projects_scanned']}**",
        f"- Configuration inputs discovered: **{totals['configuration_inputs']}**",
        f"- Inputs with detected test/runtime evidence: **{totals['covered_inputs']}**",
        f"- Aggregate key coverage: **{totals['configuration_coverage'] * 100:.1f}%**",
        f"- Total scan wall time: **{totals['runtime_seconds']:.3f}s**",
        f"- Manually reviewed false-positive examples: **{totals['reviewed_false_positives']}**",
        f"- Manually reviewed false-negative examples: **{totals['reviewed_false_negatives']}**",
        "",
        "## Manual review examples",
        "",
    ]
    any_review = False
    for item in data["projects"]:
        review = item["manual_review"]
        if not review["false_positives"] and not review["false_negatives"]:
            continue
        any_review = True
        rows.append(f"### {item['repo']}")
        rows.append("")
        for fp in review["false_positives"]:
            rows.append(f"- **FP** `{fp.get('key', fp.get('pattern', '?'))}` — {fp['reason']}")
        for fn in review["false_negatives"]:
            rows.append(f"- **FN** `{fn.get('key', fn.get('pattern', '?'))}` — {fn['reason']}")
        rows.append("")
    if not any_review:
        rows.append("No manual spot-check annotations were supplied for this run.")
        rows.append("")
    rows += [
        "## Reproduction",
        "",
        "```bash",
        "python validation/run_real_world.py --manifest validation/real_world_projects.json --reviews validation/real_world_reviews.json --json validation/results/real-world.json --markdown validation/results/real-world.md",
        "```",
        "",
        f"Runner: `{data['environment']['platform']}` / Python `{data['environment']['python']}`.",
    ]
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ConfigReach against pinned real-world OSS repositories")
    parser.add_argument("--manifest", type=Path, default=Path("validation/real_world_projects.json"))
    parser.add_argument("--reviews", type=Path, default=Path("validation/real_world_reviews.json"))
    parser.add_argument("--json", type=Path, default=Path("validation/results/real-world.json"))
    parser.add_argument("--markdown", type=Path, default=Path("validation/results/real-world.md"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    reviews = _review_map(args.reviews)
    projects: list[dict] = []
    failures: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="configreach-real-world-") as tmp:
        work = Path(tmp)
        for project in manifest["projects"]:
            try:
                projects.append(_project_result(project, work, reviews.get(project["repo"])))
            except Exception as exc:  # keep evidence for every target; fail after writing outputs
                failures.append({"repo": project["repo"], "commit": project["commit"], "error": str(exc)})
            finally:
                target = work / project["repo"].replace("/", "__")
                shutil.rmtree(target, ignore_errors=True)

    config_total = sum(item["configuration_inputs"] for item in projects)
    covered_total = sum(item["covered_inputs"] for item in projects)
    output = {
        "schema_version": 1,
        "methodology": {
            "static_only": True,
            "target_code_executed": False,
            "dependencies_installed": False,
            "pinned_commits": True,
            "manual_review_is_exhaustive": False,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "summary": {
            "projects_requested": len(manifest["projects"]),
            "projects_scanned": len(projects),
            "configuration_inputs": config_total,
            "covered_inputs": covered_total,
            "configuration_coverage": round(covered_total / config_total, 6) if config_total else 1.0,
            "runtime_seconds": round(sum(item["runtime_seconds"] for item in projects), 6),
            "reviewed_false_positives": sum(item["manual_review"]["false_positive_count"] for item in projects),
            "reviewed_false_negatives": sum(item["manual_review"]["false_negative_count"] for item in projects),
        },
        "projects": projects,
        "failures": failures,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(output), encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))
    if failures:
        for failure in failures:
            print(f"FAILED {failure['repo']}: {failure['error']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
