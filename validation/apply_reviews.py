from __future__ import annotations

import argparse
import json
from pathlib import Path

from configreach import __version__
from validation.run_real_world import _markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply committed manual reviews to existing real-world scan evidence")
    parser.add_argument("--results", type=Path, default=Path("validation/results/real-world.json"))
    parser.add_argument("--reviews", type=Path, default=Path("validation/real_world_reviews.json"))
    parser.add_argument("--markdown", type=Path, default=Path("validation/results/real-world.md"))
    parser.add_argument("--source-revision", default="")
    args = parser.parse_args()

    data = json.loads(args.results.read_text(encoding="utf-8"))
    review_doc = json.loads(args.reviews.read_text(encoding="utf-8"))
    reviews = {item["repo"]: item for item in review_doc.get("reviews", [])}

    tool = data.setdefault("tool", {})
    tool.setdefault("name", "ConfigReach")
    tool.setdefault("version", __version__)
    if args.source_revision:
        tool["source_revision"] = args.source_revision
    else:
        tool.setdefault("source_revision", "unknown")

    for project in data.get("projects", []):
        review = reviews.get(project["repo"], {})
        fps = list(review.get("false_positives", []))
        fns = list(review.get("false_negatives", []))
        project["manual_review"] = {
            "scope": review.get("scope", "not-yet-reviewed"),
            "false_positive_count": len(fps),
            "false_negative_count": len(fns),
            "false_positives": fps,
            "false_negatives": fns,
        }

    summary = data.setdefault("summary", {})
    projects = data.get("projects", [])
    summary["projects_with_manual_review"] = sum(
        1 for item in projects if item["manual_review"]["scope"] != "not-yet-reviewed"
    )
    summary["reviewed_false_positives"] = sum(
        item["manual_review"]["false_positive_count"] for item in projects
    )
    summary["reviewed_false_negatives"] = sum(
        item["manual_review"]["false_negative_count"] for item in projects
    )

    args.results.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(data), encoding="utf-8")
    print(json.dumps({
        "projects_with_manual_review": summary["projects_with_manual_review"],
        "reviewed_false_positives": summary["reviewed_false_positives"],
        "reviewed_false_negatives": summary["reviewed_false_negatives"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
