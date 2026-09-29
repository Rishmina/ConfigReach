from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from configreach import __version__
from configreach.engine import scan


def _source_revision() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _score(expected: set[str], predicted: set[str]) -> dict:
    tp = sorted(expected & predicted)
    fp = sorted(predicted - expected)
    fn = sorted(expected - predicted)
    precision = len(tp) / (len(tp) + len(fp)) if tp or fp else (1.0 if not expected else 0.0)
    recall = len(tp) / (len(tp) + len(fn)) if tp or fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "expected": len(expected),
        "predicted": len(predicted),
        "true_positives": len(tp),
        "false_positives": len(fp),
        "false_negatives": len(fn),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "tp_items": tp,
        "fp_items": fp,
        "fn_items": fn,
    }


def _predictions(report) -> dict[str, set[str]]:
    env = {
        item.name
        for item in report.keys.values()
        if item.used and "env" in item.categories
    }
    flags = {
        item.name
        for item in report.keys.values()
        if "feature-flag" in item.categories and (item.used or item.test_mentions)
    }
    declarations = {
        item.name
        for item in report.keys.values()
        if item.declarations
    }
    test_evidence = {
        item.name
        for item in report.keys.values()
        if item.test_mentions or item.runtime_observed
    }
    branches = {
        f"{item.name}::{value}"
        for item in report.keys.values()
        for value in item.branch_values
    }
    return {
        "env_var_discovery": env,
        "feature_flags": flags,
        "config_declarations": declarations,
        "test_evidence": test_evidence,
        "branch_inference": branches,
    }


def _markdown(data: dict) -> str:
    out = [
        "# ConfigReach measured accuracy",
        "",
        "Results from the repository's hand-labelled benchmark corpus. Labels are committed before scoring and include deliberately difficult positive and negative examples.",
        "",
        f"Tool: ConfigReach `{data['tool']['version']}` at source revision `{data['tool']['source_revision']}`.",
        "",
        "| Task | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, metric in data["metrics"].items():
        out.append(
            f"| {name.replace('_', ' ')} | {metric['precision'] * 100:.1f}% | {metric['recall'] * 100:.1f}% | "
            f"{metric['f1'] * 100:.1f}% | {metric['true_positives']} | {metric['false_positives']} | {metric['false_negatives']} |"
        )
    aggregate = data["aggregate"]
    out += [
        "",
        f"**Micro precision:** {aggregate['micro_precision'] * 100:.1f}%  ",
        f"**Micro recall:** {aggregate['micro_recall'] * 100:.1f}%  ",
        f"**Micro F1:** {aggregate['micro_f1'] * 100:.1f}%  ",
        f"**Macro F1:** {aggregate['macro_f1'] * 100:.1f}%",
        "",
        "## Errors exposed by the benchmark",
        "",
    ]
    for name, metric in data["metrics"].items():
        out.append(f"### {name.replace('_', ' ').title()}")
        out.append("")
        out.append("- False positives: " + (", ".join(f"`{x}`" for x in metric["fp_items"]) or "none"))
        out.append("- False negatives: " + (", ".join(f"`{x}`" for x in metric["fn_items"]) or "none"))
        out.append("")
    out += [
        "## Label policy",
        "",
    ]
    for name, policy in data["label_policy"].items():
        out.append(f"- **{name.replace('_', ' ')}:** {policy}")
    out += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "python validation/accuracy/run_accuracy.py --corpus validation/accuracy/corpus.json --json validation/results/accuracy.json --markdown validation/results/accuracy.md",
        "```",
        "",
        "This corpus is intentionally small and transparent. It measures the committed cases exactly; it is not claimed to estimate all repositories or all configuration frameworks.",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score ConfigReach against the hand-labelled corpus")
    parser.add_argument("--corpus", type=Path, default=Path("validation/accuracy/corpus.json"))
    parser.add_argument("--json", type=Path, default=Path("validation/results/accuracy.json"))
    parser.add_argument("--markdown", type=Path, default=Path("validation/results/accuracy.md"))
    args = parser.parse_args()

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="configreach-accuracy-") as tmp:
        root = Path(tmp)
        for rel, content in corpus["files"].items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        report = scan(root, use_cache=False)

    predicted = _predictions(report)
    metrics = {
        name: _score(set(corpus["labels"][name]), predicted[name])
        for name in corpus["labels"]
    }
    tp = sum(item["true_positives"] for item in metrics.values())
    fp = sum(item["false_positives"] for item in metrics.values())
    fn = sum(item["false_negatives"] for item in metrics.values())
    micro_precision = tp / (tp + fp) if tp + fp else 1.0
    micro_recall = tp / (tp + fn) if tp + fn else 1.0
    micro_f1 = 2 * micro_precision * micro_recall / (micro_precision + micro_recall) if micro_precision + micro_recall else 0.0
    output = {
        "schema_version": 1,
        "tool": {
            "name": "ConfigReach",
            "version": __version__,
            "source_revision": _source_revision(),
        },
        "corpus": corpus["name"],
        "label_policy": corpus["label_policy"],
        "designed_challenges": corpus.get("designed_challenges", []),
        "metrics": metrics,
        "aggregate": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "micro_precision": round(micro_precision, 6),
            "micro_recall": round(micro_recall, 6),
            "micro_f1": round(micro_f1, 6),
            "macro_f1": round(sum(item["f1"] for item in metrics.values()) / len(metrics), 6),
        },
        "scan_summary": {
            "configuration_inputs": report.effective_total,
            "files_scanned": report.files_scanned,
            "tests_scanned": report.tests_scanned,
        },
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(output), encoding="utf-8")
    print(json.dumps(output["aggregate"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
