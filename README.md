# ConfigReach

> **Your tests have 94% code coverage. But only 31% configuration coverage. ConfigReach tells you the difference.**

**ConfigReach is configuration coverage for your test suite — a deterministic, CPU-only, offline analyzer that shows which runtime configuration inputs your tests actually exercise.** Think **Codecov for configuration space**.

[![CI](https://github.com/sauravsingla/ConfigReach/actions/workflows/ci.yml/badge.svg)](https://github.com/sauravsingla/ConfigReach/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sauravsingla/ConfigReach/actions/workflows/codeql.yml/badge.svg)](https://github.com/sauravsingla/ConfigReach/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

ConfigReach does **not** need a GPU, LLM, API key, hosted service or telemetry. The same repository produces the same static analysis result.

## The problem

Code coverage can tell you that a line executed. It cannot tell you whether the configurations that change that line's behavior were exercised.

```python
mode = os.getenv("PAYMENT_MODE", "sandbox")
if mode == "live":
    charge_real_card()
else:
    simulate_charge()
```

A test suite can execute this code every time and still never test `PAYMENT_MODE=live`.

ConfigReach builds a repository-wide inventory of configuration reads and declarations, maps them to test evidence, and reports the missing configuration states.

## Quick start

```bash
git clone https://github.com/sauravsingla/ConfigReach.git
cd ConfigReach
python -m pip install -e .
configreach scan .
```

Run the bundled fixture:

```bash
configreach scan examples/basic
configreach explain PAYMENT_MODE examples/basic
configreach matrix examples/basic
```

## What v0.1 detects

| Ecosystem | Examples | v0.1 depth |
|---|---|---|
| Python | `os.getenv`, `os.environ[...]`, `os.environ.get` | AST-backed |
| Python CLI | `argparse.add_argument("--flag")` | AST-backed |
| JavaScript / TypeScript | `process.env.KEY`, `process.env["KEY"]` | conservative static pattern |
| Go | `os.Getenv`, `os.LookupEnv` | conservative static pattern |
| Java | `System.getenv`, `System.getProperty` | conservative static pattern |
| Rust | `env::var`, `std::env::var` | conservative static pattern |
| Ruby | `ENV[...]`, `ENV.fetch(...)` | conservative static pattern |
| PHP | `getenv(...)` | conservative static pattern |

ConfigReach also recognizes `.env*` templates, JSON, TOML, INI/CFG, conservative YAML environment declarations, Terraform variables and Makefile variables. The architecture is intentionally adapter-based; v0.1 does **not** claim equal semantic depth across every language.

## Commands

```bash
configreach scan [PATH]
configreach coverage [PATH]
configreach explain KEY [PATH]
configreach matrix [PATH]
configreach diff origin/main...HEAD [PATH]
configreach doctor [PATH]
configreach export [PATH] --format json
configreach export [PATH] --format sarif
configreach init [PATH]
configreach trace --path . -- pytest -q
```

### Reports and CI gating

```bash
configreach scan .
configreach scan . --format json --output configreach.json
configreach scan . --format markdown --output configreach.md
configreach scan . --format sarif --output configreach.sarif
configreach scan . --fail-under 70
```

`--fail-under` uses an observable metric: discovered configuration inputs with detected test evidence divided by total discovered inputs.

### Explain and matrix

```bash
configreach explain PAYMENT_MODE .
configreach matrix .
```

`explain` shows source reads, declarations, test references, inferred expected values and statically observed test values. `matrix` emits a simple tab-separated key/coverage/usage/declaration view.

### PR-oriented diff

```bash
configreach diff origin/main...HEAD
```

This maps changed files to configuration inputs and highlights configuration touched by the PR without detected test evidence.

### Optional Python runtime tracing

```bash
configreach trace -- pytest -q
```

The initial dynamic tracer is deliberately narrow: it runs supported Python commands inside a tracing wrapper and writes key names plus short SHA-256-derived value fingerprints to `.configreach/trace.jsonl`; raw runtime values are not persisted. The static core remains fully useful without tracing.

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
```

For SARIF code-scanning annotations, generate `configreach.sarif` and upload it with GitHub's standard `github/codeql-action/upload-sarif` action.

## Configuration

```bash
configreach init
```

```toml
[configreach]
fail_under = 60
ignore = ["vendor/**", "generated/**"]
test_patterns = ["tests/**", "**/test_*.py", "**/*.spec.ts"]
```

## What counts as coverage?

- **Key coverage**: a discovered configuration input has evidence in a detected test file.
- **Static value evidence**: a test visibly assigns a value through a pattern the adapter understands, such as `monkeypatch.setenv("MODE", "live")`.
- **Expected values**: values inferred from explicit comparisons or declaration metadata such as argparse `choices`.
- **Value coverage**: tested expected values divided by discovered expected values, when the expected domain is knowable.

Unknown values remain unknown. ConfigReach does not invent a quality score or ask an LLM to guess whether a configuration is “probably covered.”

## Findings beyond coverage

The report model also exposes configuration read but not declared, configuration declared but not read, source provenance for reads/declarations/tests, redacted sensitive-looking defaults, and PR-level configuration touched by changed files.

## Performance and safety

ConfigReach skips common VCS/dependency/build directories and files larger than 2 MB by default. Static scanning does not execute target code or access the network. Dynamic tracing is opt-in and executes exactly the Python command supplied by the user.

See [architecture](docs/architecture.md), [threat model](docs/threat-model.md) and [roadmap](docs/roadmap.md).

## Roadmap highlights

- deeper AST-backed JavaScript/TypeScript and Go adapters,
- boolean and enum branch accounting,
- baseline files and changed-lines gating,
- pairwise configuration-combination coverage,
- monorepo incremental caching,
- searchable static HTML configuration graph,
- GitHub PR comment helper,
- adapter/plugin SDK.

## Contributing

Contributions are welcome, especially reproducible fixtures for language/framework-specific configuration idioms. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security and privacy

Static analysis is local, deterministic and network-free. ConfigReach is not a secret scanner; sensitive-looking values are redacted as defense in depth. See [SECURITY.md](SECURITY.md) and the [threat model](docs/threat-model.md).

## License

MIT — see [LICENSE](LICENSE).
