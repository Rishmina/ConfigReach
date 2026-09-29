# Roadmap

## v0.1 — deterministic foundation ✅
- Python AST discovery for `os.getenv`, `os.environ`, argparse and comparisons.
- Cross-language environment-read detection for JavaScript/TypeScript, Go, Java, Rust, Ruby and PHP.
- dotenv, JSON, TOML, INI, YAML, Terraform and Make declaration discovery.
- Test-reference and static test-value evidence.
- text, JSON, Markdown and SARIF reporters.

## v0.2 — repository-scale coverage foundation ✅
- Pydantic settings and generic feature-flag discovery.
- Dockerfile, properties, Helm-values and GitHub Actions configuration discovery.
- Boolean/value coverage and deterministic pairwise key-combination coverage.
- Legacy baseline files.
- Persistent repository scan cache.
- Package-root detection for monorepos.
- Searchable standalone HTML configuration graph.
- GitHub-ready PR comment generation and an example auto-comment workflow.
- Entry-point based adapter/plugin SDK.
- Additional deterministic findings for known untested values, sensitive defaults and likely naming inconsistencies.

## v0.3 — deeper language semantics
- AST-backed JavaScript/TypeScript and Go adapters.
- Framework adapters for Spring, .NET configuration and popular feature-flag SDKs.
- Function-level configuration dependency graph instead of file-level pairwise approximation.
- Changed-line-aware base/head comparison without requiring a second checkout.
- Workspace-local incremental cache invalidation for very large monorepos.

## v0.4 — richer testing guidance
- N-wise combination planning without executing generated tests.
- Explicit validator-domain extraction across languages.
- Test fixture suggestions exported as deterministic data, not generated prose.

## v1.0
- Stable report schema and plugin contract.
- Versioned adapter capability matrix.
- Reproducibility suite across operating systems and Python versions.
