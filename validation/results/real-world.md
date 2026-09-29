# ConfigReach real-world validation

Static scans of pinned upstream commits. Target projects are not executed and their dependencies are not installed.
Runtime is wall-clock scan time on the recorded runner and is therefore performance evidence, not a cross-machine guarantee.
Manual false-positive/false-negative entries are targeted spot checks, not exhaustive repository-wide error rates; measured accuracy comes from the hand-labelled corpus.

The scan counts below were produced by the successful external-project validation run on ConfigReach 0.9.1. The manual-review columns were subsequently populated from committed human spot checks; they do not alter the scan counts or coverage values.

| Project | Ecosystem | Configs | Covered | Coverage | Runtime | Reviewed FP | Reviewed FN |
|---|---|---:|---:|---:|---:|---:|---:|
| pallets/flask | Python | 161 | 24 | 14.9% | 0.851s | 0 | 0 |
| django/django | Python | 396 | 136 | 34.3% | 75.942s | 0 | 1 |
| pydantic/pydantic | Python | 817 | 31 | 3.8% | 55.008s | 0 | 0 |
| encode/httpx | Python | 61 | 5 | 8.2% | 0.760s | 0 | 0 |
| expressjs/express | JavaScript | 68 | 4 | 5.9% | 0.821s | 2 | 0 |
| axios/axios | JavaScript | 7477 | 28 | 0.4% | 148.797s | 2 | 0 |
| gin-gonic/gin | Go | 16 | 2 | 12.5% | 0.420s | 0 | 0 |
| helm/helm | Go | 476 | 106 | 22.3% | 13.806s | 0 | 0 |
| spring-projects/spring-petclinic | Java/Spring | 100 | 30 | 30.0% | 0.221s | 0 | 0 |
| hashicorp/terraform | Go/Terraform | 8444 | 273 | 3.2% | 1514.837s | 0 | 2 |

## Aggregate

- Projects scanned: **10**
- Configuration inputs discovered: **18016**
- Inputs with detected test/runtime evidence: **639**
- Aggregate key coverage: **3.5%**
- Total scan wall time: **1811.463s**
- Projects with targeted manual review: **4**
- Manually reviewed false-positive examples: **4**
- Manually reviewed false-negative examples: **3**

## Manual review examples

### django/django

- **FN** `DJANGO_SETTINGS_MODULE` (`django/conf/__init__.py`) — the environment-variable name is stored in `ENVIRONMENT_VARIABLE` and passed to `os.environ.get` indirectly; the current Python discovery path requires a literal key at the call site.

### hashicorp/terraform

- **FN** `TF_TEMP_LOG_PATH` (`main.go`) — the key is held in `envTmpLogPath` and passed to `os.Getenv`; the current Go adapter does not perform constant propagation.
- **FN** `TF_IN_AUTOMATION` (`commands.go`) — the key is held in `runningInAutomationEnvName` and passed to `os.Getenv`; the current Go adapter does not perform constant propagation.

### expressjs/express

- **FP** `name` (`package.json`) — package identity metadata is not runtime configuration, but generic JSON flattening currently records it as a settings declaration.
- **FP** `version` (`package.json`) — package release metadata is not runtime configuration, but generic JSON flattening currently records it as a settings declaration.

### axios/axios

- **FP** `name` (`package.json`) — package identity metadata is not runtime configuration, but generic JSON flattening currently records it as a settings declaration.
- **FP** `version` (`package.json`) — package release metadata is not runtime configuration, but generic JSON flattening currently records it as a settings declaration.

See [`manual-review.md`](manual-review.md) and [`../real_world_reviews.json`](../real_world_reviews.json) for the review source of truth.

## Reproduction

```bash
python validation/run_real_world.py --manifest validation/real_world_projects.json --reviews validation/real_world_reviews.json --json validation/results/real-world.json --markdown validation/results/real-world.md
```

Runner for the published scan: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39` / Python `3.12.14`.

The external repositories are pinned by commit SHA in `validation/real_world_projects.json`. Inclusion here is validation against external code, not endorsement by those projects.
