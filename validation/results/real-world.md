# ConfigReach real-world validation

Static scans of pinned upstream commits. Target projects are not executed and their dependencies are not installed.
Runtime is wall-clock scan time on the recorded runner and is therefore performance evidence, not a cross-machine guarantee.
Manual false-positive/false-negative entries are targeted spot checks, not exhaustive repository-wide error rates; measured accuracy comes from the hand-labelled corpus.

Tool: ConfigReach `0.9.1` at source revision `c9b5d5d1b9c62bcc45ad71e90677535943897472`.

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
- Projects with manual spot checks: **4**
- Manually reviewed false-positive examples: **4**
- Manually reviewed false-negative examples: **3**

## Manual review examples

### django/django

Review scope: Reviewed environment-variable indirection in django/conf/__init__.py at the pinned commit.

- **FN** `DJANGO_SETTINGS_MODULE` (django/conf/__init__.py) — The environment-variable name is stored in ENVIRONMENT_VARIABLE and passed to os.environ.get indirectly; the current Python discovery path requires a literal key at the call site.

### expressjs/express

Review scope: Reviewed package.json metadata alongside real NODE_ENV reads at the pinned commit.

- **FP** `name` (package.json) — The package name is project metadata, not an application runtime configuration input, but generic JSON flattening currently records it as a settings declaration.
- **FP** `version` (package.json) — The package version is release metadata rather than runtime configuration; generic JSON flattening currently records it as a settings declaration.

### axios/axios

Review scope: Reviewed package.json metadata in a large JavaScript repository at the pinned commit.

- **FP** `name` (package.json) — The package identity is metadata, not runtime configuration; generic JSON flattening treats it as a configuration declaration.
- **FP** `version` (package.json) — The package version is metadata, not runtime configuration; generic JSON flattening treats it as a configuration declaration.

### hashicorp/terraform

Review scope: Reviewed Go environment-variable reads whose names are held in constants at the pinned commit.

- **FN** `TF_TEMP_LOG_PATH` (main.go) — Terraform defines envTmpLogPath = "TF_TEMP_LOG_PATH" and calls os.Getenv(envTmpLogPath); the current Go adapter recognizes literal os.Getenv/os.LookupEnv keys only.
- **FN** `TF_IN_AUTOMATION` (commands.go) — Terraform defines runningInAutomationEnvName = "TF_IN_AUTOMATION" and calls os.Getenv(runningInAutomationEnvName); constant propagation across the Go file is not implemented.

## Reproduction

```bash
python validation/run_real_world.py --manifest validation/real_world_projects.json --reviews validation/real_world_reviews.json --json validation/results/real-world.json --markdown validation/results/real-world.md
```

Runner: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39` / Python `3.12.14`.
