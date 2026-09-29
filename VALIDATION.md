# ConfigReach validation and measured accuracy

ConfigReach publishes two deliberately separate forms of evidence:

1. **External-project validation**: static scans of pinned commits from recognizable open-source repositories, recording configuration inputs discovered, detected test evidence, configuration coverage, runtime and targeted manual false-positive/false-negative reviews.
2. **Hand-labelled accuracy benchmark**: a committed ground-truth corpus scored for precision, recall and F1 across environment-variable discovery, feature flags, configuration declarations, test evidence and branch inference.

These are not the same thing. Configuration coverage observed in an external repository is not ground truth. Precision/recall claims come only from the hand-labelled corpus.

## Current measured accuracy

The committed benchmark currently reports:

| Task | Precision | Recall | F1 |
|---|---:|---:|---:|
| Environment-variable discovery | 100.0% | 72.7% | 84.2% |
| Feature flags | 50.0% | 100.0% | 66.7% |
| Configuration declarations | 66.7% | 90.9% | 76.9% |
| Test evidence | 100.0% | 100.0% | 100.0% |
| Branch inference | 53.8% | 100.0% | 70.0% |

Aggregate metrics on the committed label set:

- **Micro precision:** 71.7%
- **Micro recall:** 89.2%
- **Micro F1:** 79.5%
- **Macro F1:** 79.6%

See [`validation/results/accuracy.md`](validation/results/accuracy.md) for the generated table, exact false positives/false negatives and label policy, and [`validation/results/accuracy.json`](validation/results/accuracy.json) for machine-readable evidence.

### What the benchmark currently exposes

- Environment-variable discovery misses some statically recoverable indirection, including Python key construction, JavaScript `process.env` destructuring and Go variable-key lookups.
- The feature-flag heuristic can over-classify unrelated methods named `variation`.
- Generic JSON/TOML declaration discovery can treat package/project metadata as runtime configuration.
- Boolean finite domains can currently be over-counted as branch states even when no decision branch exists.
- The committed test-evidence cases are all detected, but that task has a small labelled sample and should not be interpreted as universal 100% accuracy.

Publishing these errors is intentional: the purpose of this benchmark is to make limitations visible and reproducible rather than imply perfect analysis.

## Real-world external-project suite

The suite covers **10 pinned open-source repositories** across Python, JavaScript, Go, Java/Spring and Terraform:

- `pallets/flask`
- `django/django`
- `pydantic/pydantic`
- `encode/httpx`
- `expressjs/express`
- `axios/axios`
- `gin-gonic/gin`
- `helm/helm`
- `spring-projects/spring-petclinic`
- `hashicorp/terraform`

The published scan observed **18,016 configuration inputs**, **639 inputs with detected test/runtime evidence**, **3.5% aggregate key coverage**, and **1,811.463 seconds total scan wall time** across the 10 pinned projects. These are ConfigReach observations, not ground-truth accuracy measurements.

The exact upstream commit SHAs are committed in [`validation/real_world_projects.json`](validation/real_world_projects.json). ConfigReach does not execute those projects or install their dependencies during this validation; it performs static analysis only.

The per-project table is published at [`validation/results/real-world.md`](validation/results/real-world.md), with the original machine-readable scan output at [`validation/results/real-world.json`](validation/results/real-world.json).

### Manual real-world review

Targeted spot checks currently cover **4 projects**, with **4 reviewed false-positive examples** and **3 reviewed false-negative examples**. The human-readable report is [`validation/results/manual-review.md`](validation/results/manual-review.md), and the machine-readable summary is [`validation/results/manual-review.json`](validation/results/manual-review.json). The review source of truth is [`validation/real_world_reviews.json`](validation/real_world_reviews.json).

Examples include:

- **Django false negative:** `DJANGO_SETTINGS_MODULE` is read through a constant (`ENVIRONMENT_VARIABLE`) passed to `os.environ.get`, which the current literal-key Python discovery path does not resolve.
- **Terraform false negatives:** `TF_TEMP_LOG_PATH` and `TF_IN_AUTOMATION` are read through Go constants passed to `os.Getenv`; the current Go adapter does not perform constant propagation.
- **Express / Axios false positives:** `package.json` `name` and `version` are project metadata, but generic JSON flattening currently records them as configuration declarations.

These annotations are **targeted reviewed examples, not exhaustive repository-wide FP/FN rates**. The hand-labelled corpus is the source for precision/recall metrics.

## Reproduce

Measured accuracy:

```bash
python validation/accuracy/run_accuracy.py \
  --corpus validation/accuracy/corpus.json \
  --json validation/results/accuracy.json \
  --markdown validation/results/accuracy.md
```

Real-world suite (network access required to fetch pinned GitHub commits):

```bash
python validation/run_real_world.py \
  --manifest validation/real_world_projects.json \
  --reviews validation/real_world_reviews.json \
  --json validation/results/real-world.json \
  --markdown validation/results/real-world.md
```

The GitHub Actions workflow [`validation.yml`](.github/workflows/validation.yml) runs both suites, uploads the evidence as an artifact and commits generated Markdown/JSON results back to `main` when they change. Its publication step rebases generated evidence onto the latest `main` before pushing, so unrelated documentation changes cannot make a long validation run stale.

## Claim boundaries

- The accuracy corpus is intentionally small, transparent and adversarial; it does **not** estimate performance on every language/framework.
- External-project coverage figures are ConfigReach observations, not independently labelled ground truth.
- Manual external-project reviews are spot checks, not statistical error-rate estimates.
- Runtime is wall-clock time on the recorded runner and is not hardware-independent.
- Upstream projects are used as external validation targets; their inclusion does not imply endorsement of ConfigReach by those projects.
