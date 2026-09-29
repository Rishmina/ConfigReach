# Roadmap

## v0.1 — deterministic foundation
- Python AST discovery for `os.getenv`, `os.environ`, argparse and comparisons.
- Cross-language environment-read detection for JavaScript/TypeScript, Go, Java, Rust, Ruby and PHP.
- dotenv, JSON, TOML, INI, YAML, Terraform and Make declaration discovery.
- Test-reference and static test-value evidence.
- text, JSON, Markdown and SARIF reporters.
- PR-oriented `diff`, `explain`, `matrix`, `doctor`, `init` and Python `trace` commands.

## v0.2 — stronger value and branch coverage
- AST-backed JavaScript/TypeScript and Go adapters.
- Boolean/enum branch accounting.
- Baseline files and changed-lines gating.
- Pairwise configuration-combination coverage.

## v0.3 — repository-scale analysis
- Monorepo workspaces and incremental cache.
- HTML configuration graph with source links.
- GitHub PR comment helper and SARIF upload example.
- Adapter/plugin SDK.

## v1.0
- Stable report schema, documented adapter contract and reproducible cross-language fixtures.
