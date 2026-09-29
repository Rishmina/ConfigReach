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
- Legacy baselines, persistent cache and package-root detection for monorepos.
- Searchable standalone HTML graph, PR comments and entry-point plugin SDK.
- Deterministic findings for untested values, sensitive defaults and naming inconsistencies.

## v0.3 — semantic coverage and PR deltas ✅
- Function-scoped Python configuration dependency graph.
- Branch source provenance.
- `Literal`, Enum and bool annotation domains for Python settings.
- Explicit pairwise value-state coverage based on test scenarios.
- Merge-base vs current-tree PR scanning for newly introduced keys, removed keys and changed value/default/branch domains.
- Findings for explicit default-only testing and global-environment test mutation.
- Cross-version cache schema invalidation and Python 3.11–3.13 CI coverage.

## v0.4 — deeper language semantics
- Parser/AST-backed JavaScript/TypeScript and Go adapters while preserving a zero-dependency core through optional adapters.
- Framework adapters for Spring, .NET configuration and additional feature-flag SDKs.
- Changed-line dependency slicing beyond file-level touched-key detection.
- Workspace-local incremental cache invalidation for very large monorepos.
- Richer validator-domain extraction across languages.

## v0.5 — testing guidance
- Deterministic N-wise combination planning without executing generated tests.
- Test fixture suggestions exported as structured deterministic data, not generated prose.

## v1.0
- Stable report schema and plugin contract.
- Versioned adapter capability matrix.
- Reproducibility suite across operating systems and supported Python versions.
