# ConfigReach

> **Your tests have 94% code coverage. But only 31% configuration coverage. ConfigReach tells you the difference.**

**ConfigReach is configuration coverage for your test suite — a deterministic, CPU-only, offline analyzer that shows which runtime configuration inputs your tests actually exercise.** Think **Codecov for configuration space**.

[![CI](https://github.com/sauravsingla/ConfigReach/actions/workflows/ci.yml/badge.svg)](https://github.com/sauravsingla/ConfigReach/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sauravsingla/ConfigReach/actions/workflows/codeql.yml/badge.svg)](https://github.com/sauravsingla/ConfigReach/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Runtime dependencies: 0](https://img.shields.io/badge/runtime%20dependencies-0-brightgreen.svg)](pyproject.toml)

ConfigReach needs **no GPU, no LLM, no API key, no hosted service, no telemetry and no paid dependency**. Static analysis does not execute the target repository. Machine-readable results are deterministic for the same repository state and configuration.

![ConfigReach terminal example](docs/demo.svg)

## Why configuration coverage?

Code coverage can tell you that a line executed. It cannot tell you whether the configuration states that change that line's behavior were exercised.

```python
mode = os.getenv("PAYMENT_MODE", "sandbox")
if mode == "live":
    charge_real_card()
else:
    simulate_charge()
```

A test suite can execute this code on every run and still never test `PAYMENT_MODE=live`.

ConfigReach inventories configuration reads and declarations, maps them to test evidence, and reports missing keys, missing known values, boolean-state gaps, interacting settings, declaration drift and PR blast radius.

## Quick start

```bash
git clone https://github.com/sauravsingla/ConfigReach.git
cd ConfigReach
python -m pip install -e .
configreach scan .
```

Try the polyglot fixture:

```bash
configreach scan examples/polyglot
configreach explain PAYMENT_MODE examples/polyglot
configreach matrix examples/polyglot
configreach scan examples/polyglot --format html --output configreach.html
```

## Metrics — no opaque score

ConfigReach reports observable metrics separately:

- **Key coverage** — discovered configuration inputs with detected test/runtime evidence.
- **Value coverage** — explicitly tested values / explicitly known values.
- **Boolean coverage** — tested `true`/`false` states where a boolean domain can be established.
- **Pairwise configuration coverage** — interacting keys read in the same source file that are referenced together in at least one test file.
- **Blast radius** — distinct files/modules that read a key.

Unknown domains remain unknown. ConfigReach never asks a model whether something is “probably covered.” See [docs/metrics.md](docs/metrics.md).

## Discovery coverage

### Runtime reads

| Ecosystem | Examples | Analysis |
|---|---|---|
| Python | `os.getenv`, `os.environ[...]`, `os.environ.get`, `setdefault` | AST-backed |
| Pydantic Settings | `BaseSettings` fields and aliases | AST-backed |
| Python CLI | `argparse`, common Click/Typer option forms | AST-backed/conservative |
| Feature flags | `is_enabled`, `feature_enabled`, LaunchDarkly-style `variation` | AST + conservative patterns |
| JavaScript / TypeScript | `process.env.KEY`, `process.env["KEY"]`, selected Deno/Bun forms | conservative static pattern |
| Go | `os.Getenv`, `os.LookupEnv` | conservative static pattern |
| Java | `System.getenv`, `System.getProperty` | conservative static pattern |
| Rust | `env::var`, `env::var_os` | conservative static pattern |
| Ruby | `ENV[...]`, `ENV.fetch(...)` | conservative static pattern |
| PHP | `getenv(...)`, common `env(...)` form | conservative static pattern |
| Shell | `$VAR`, `${VAR}` | conservative static pattern |

### Declarations and deployment sources

ConfigReach recognizes:

`.env.example`, `.env.template`, other `.env*` templates, JSON, TOML, INI/CFG, Java properties, YAML environment declarations, Dockerfiles/Containerfiles, Docker Compose environment blocks, Kubernetes-style `name:` environment declarations, Helm `values.yaml`, GitHub Actions `${{ vars.* }}` and `${{ secrets.* }}`, Terraform variables, Makefile variables, Pydantic settings fields and CLI options.

The core is deliberately honest about support depth: Python gets semantic AST analysis today; most other languages currently use conservative deterministic patterns. Deeper language adapters are on the roadmap.

## Commands

```bash
configreach scan [PATH]
configreach coverage [PATH]
configreach explain KEY [PATH]
configreach matrix [PATH]
configreach diff origin/main...HEAD [PATH]
configreach pr-comment origin/main...HEAD [PATH]
configreach doctor [PATH]
configreach export [PATH] --format json
configreach export [PATH] --format sarif
configreach export [PATH] --format html
configreach baseline create [PATH]
configreach cache clear [PATH]
configreach init [PATH]
configreach trace --path . -- pytest -q
```

### Scan and CI gating

```bash
configreach scan . --fail-under 70
configreach scan . --fail-on error
configreach scan . --fail-on uncovered
configreach scan . --fail-on untested-values
configreach scan . --format sarif --output configreach.sarif
```

`--fail-under` gates key coverage. `--fail-on` can gate finding names (`uncovered`, `undeclared`, `untested-values`, `unsafe-default`), severities (`warning`, `error`) or rule IDs (`CR001`, `CR005`, ...).

### Explain one key

```bash
configreach explain PAYMENT_MODE .
```

Shows reads, declarations, tests, known/tested values, validators, runtime observation and blast radius.

### Pull-request configuration diff

```bash
configreach diff origin/main...HEAD
configreach pr-comment origin/main...HEAD --output /tmp/configreach-comment.md
```

The PR report identifies configuration touched by changed files, whether test evidence exists, and how many files the setting can affect. The repository includes an example workflow that creates or updates a ConfigReach PR comment for same-repository pull requests.

### Searchable static HTML graph

```bash
configreach scan . --format html --output configreach.html
```

The HTML report is a single static file with no CDN or network dependency. It includes a searchable matrix plus a configuration graph linking every key to detected reads, declarations and test locations.

### Legacy baselines

Adopt ConfigReach without failing CI on historical gaps:

```bash
configreach baseline create .
```

Baseline keys remain visible but are excluded from CI gating. New keys are not silently added. See [docs/baselines.md](docs/baselines.md).

### Persistent cache

Caching is enabled by default and stored under `.configreach/cache/`. It caches the redacted deterministic model and invalidates when eligible repository file metadata or ConfigReach configuration changes.

```bash
configreach scan . --no-cache
configreach cache clear .
```

Timing/cache-hit state is deliberately excluded from JSON/SARIF result semantics so machine output remains reproducible.

### Optional Python runtime trace

```bash
configreach trace -- pytest -q
configreach scan .
```

Tracing is optional. It records configuration key names plus short SHA-256-derived value fingerprints to `.configreach/trace.jsonl`; raw runtime values are not persisted. The scanner consumes the trace as runtime evidence. Static analysis remains fully usable without tracing.

## Findings

| Rule | Meaning | Default severity |
|---|---|---|
| `CR001` | discovered configuration has no detected test/runtime evidence | warning |
| `CR002` | configuration read by application code but not declared in a recognized source | warning |
| `CR003` | configuration declared but not read by recognized application code | note |
| `CR004` | known configuration values are not all exercised | warning |
| `CR005` | sensitive-looking configuration has a non-empty static default | error |
| `CR006` | likely inconsistent names normalize to the same identifier | warning |
| `CR007` | production-like known value (`live`, `prod`, etc.) is not exercised | warning |

These findings are deterministic heuristics, not claims of semantic certainty. Source provenance is included so every finding can be inspected.

## GitHub Actions

```yaml
name: Configuration coverage
on: [pull_request]

jobs:
  configreach:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: sauravsingla/ConfigReach@main
        with:
          path: .
          format: markdown
          fail-under: "60"
          fail-on: error
```

Markdown output is appended to the GitHub job summary. SARIF can be generated and uploaded with GitHub's standard Code Scanning action.

An optional PR-comment workflow is included at [`.github/workflows/configreach-pr.yml`](.github/workflows/configreach-pr.yml). It uses the GitHub API only in the workflow layer; the ConfigReach analyzer itself remains network-free.

## Configuration

Create a starter configuration:

```bash
configreach init
```

```toml
[configreach]
fail_under = 60
fail_on = ["error"]
ignore = ["vendor/**", "generated/**"]
test_patterns = ["tests/**", "**/test_*.py", "**/*.spec.ts"]
baseline = ".configreach/baseline.json"
trace_file = ".configreach/trace.jsonl"
cache = true
plugins = true
```

## Monorepos

ConfigReach detects package roots from Python, Node, Go, Rust, Maven and Gradle manifests and exposes them in the report. Source provenance remains repository-relative, so reports can be grouped by package without rewriting paths.

## Adapter plugin SDK

Third-party packages can register deterministic adapters through the `configreach.adapters` entry-point group. Plugin failures are isolated into scanner warnings. See [docs/plugin-sdk.md](docs/plugin-sdk.md).

## Performance benchmark

A synthetic benchmark is included:

```bash
python benchmarks/bench_scan.py 1000
```

It generates a temporary repository and measures a cold, no-cache CPU scan. Benchmark output is environment-dependent and is intentionally not used as a quality score.

## Testing

```bash
python -m pip install -e ".[dev]"
pytest
python -m compileall -q src tests
```

The test suite covers core discovery, multi-language reads, deployment/config sources, Pydantic settings, feature flags, boolean/value/pairwise metrics, baselines, cache round-trips, HTML/SARIF/JSON/Markdown reporters, secret redaction, deterministic generated inventories and CLI policy behavior.

## Design principles

- CPU-only and zero runtime dependencies.
- No network, telemetry, model inference or paid API in the core.
- Static scanning never executes target application code.
- Runtime tracing is explicit opt-in.
- Sensitive values are redacted before serialization.
- Unknown is preferable to fabricated certainty.
- Every finding has inspectable source provenance.
- Machine-readable result semantics are reproducible.

See [architecture](docs/architecture.md), [metrics](docs/metrics.md), [threat model](docs/threat-model.md), [plugin SDK](docs/plugin-sdk.md) and [roadmap](docs/roadmap.md).

## Contributing

Contributions are welcome, especially small reproducible fixtures for language/framework-specific configuration idioms. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security and privacy

Static analysis is local, deterministic and network-free. ConfigReach is not a credential validator or a replacement for a dedicated secret scanner. See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

## License

MIT — see [LICENSE](LICENSE).
