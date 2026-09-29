# Validation

This directory separates two different kinds of evidence:

1. **Real-world external-project scans** — ConfigReach is run against pinned commits from recognizable open-source projects. These runs measure discovered configuration inputs, detected test evidence, configuration coverage, scan runtime, findings and manually reviewed false-positive/false-negative examples. Target application code is not executed and target dependencies are not installed.
2. **Hand-labelled accuracy benchmark** — a small transparent corpus with labels committed independently of scanner output. The scorer publishes precision, recall and F1 for environment-variable discovery, feature flags, configuration declarations, test evidence and branch inference.

The two should not be conflated. Real-world configuration coverage describes what ConfigReach observes in those repositories; it is **not** ground truth. The hand-labelled corpus is the place where ground-truth classification metrics are computed.

## Reproduce measured accuracy

```bash
python validation/accuracy/run_accuracy.py \
  --corpus validation/accuracy/corpus.json \
  --json validation/results/accuracy.json \
  --markdown validation/results/accuracy.md
```

The corpus includes deliberately difficult cases rather than only supported happy paths: dynamic environment-key construction, JavaScript `process.env` destructuring, Go variable-key lookups, unrelated `variation(...)` calls, project metadata that should not be treated as runtime configuration, helper-mediated test evidence and boolean domains without actual decision branches.

## Reproduce real-world validation

The external suite requires network access because it fetches pinned GitHub commits:

```bash
python validation/run_real_world.py \
  --manifest validation/real_world_projects.json \
  --reviews validation/real_world_reviews.json \
  --json validation/results/real-world.json \
  --markdown validation/results/real-world.md
```

The repository CI workflow runs both suites and publishes the generated JSON/Markdown. Upstream projects are pinned by commit SHA so later upstream changes cannot silently change a published result.

## Manual review policy

Real-world false positives and false negatives are reported as **targeted manual spot checks**, not as exhaustive error rates over the entire upstream repository. Every annotation must include the project, key/pattern and a short reason. The report explicitly states this limitation.

Precision/recall claims come only from the hand-labelled corpus, where the complete committed label set is available for inspection.

## Interpreting runtime

Runtime is wall-clock static scan time on the recorded GitHub-hosted runner. It is useful for reproducibility and order-of-magnitude comparison but is not a hardware-independent performance guarantee.
