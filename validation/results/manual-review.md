# ConfigReach real-world manual review

This report records **targeted human spot checks** against pinned external open-source repositories. It is intentionally separate from the hand-labelled accuracy benchmark.

These examples are concrete observed failure modes, **not exhaustive repository-wide false-positive/false-negative rates**.

## Summary

- Projects with targeted manual review: **4**
- Reviewed false-positive examples: **4**
- Reviewed false-negative examples: **3**

## django/django

Pinned commit: `9332b163a67eabe5bdbf8066b1c5da394be9aa9c`

### False negatives

- `DJANGO_SETTINGS_MODULE` — `django/conf/__init__.py` defines `ENVIRONMENT_VARIABLE = "DJANGO_SETTINGS_MODULE"` and later calls `os.environ.get(ENVIRONMENT_VARIABLE)`. The current Python environment-variable discovery requires a literal key at the call site and therefore misses this simple constant indirection.

### False positives

- None in this targeted review.

## hashicorp/terraform

Pinned commit: `50ffbe06bd26cb5b4d2016e47b51b43aea74a8b0`

### False negatives

- `TF_TEMP_LOG_PATH` — `main.go` defines `envTmpLogPath = "TF_TEMP_LOG_PATH"` and later calls `os.Getenv(envTmpLogPath)`. The current Go adapter recognizes literal `os.Getenv` / `os.LookupEnv` keys but does not perform constant propagation.
- `TF_IN_AUTOMATION` — `commands.go` defines `runningInAutomationEnvName = "TF_IN_AUTOMATION"` and later calls `os.Getenv(runningInAutomationEnvName)`. This is the same constant-propagation limitation.

### False positives

- None in this targeted review.

## expressjs/express

Pinned commit: `7ef98448f8b38099ab1ded55e458538ad47a51e7`

### False positives

- `name` — `package.json` package identity metadata is not application runtime configuration, but generic JSON flattening currently records it as a settings declaration.
- `version` — `package.json` release metadata is not application runtime configuration, but generic JSON flattening currently records it as a settings declaration.

### False negatives

- None in this targeted review.

## axios/axios

Pinned commit: `2426e03ba9020be31ed013873423cea6b7cd2e67`

### False positives

- `name` — `package.json` package identity metadata is not runtime configuration, but generic JSON flattening currently records it as a settings declaration.
- `version` — `package.json` release metadata is not runtime configuration, but generic JSON flattening currently records it as a settings declaration.

### False negatives

- None in this targeted review.

## Reproducibility and source of truth

The machine-readable review annotations are committed in [`../real_world_reviews.json`](../real_world_reviews.json). The external repositories and exact pinned commits are committed in [`../real_world_projects.json`](../real_world_projects.json).

Measured precision/recall is **not** calculated from these spot checks. See [`accuracy.md`](accuracy.md) for the complete-label benchmark and its precision/recall/F1 metrics.
