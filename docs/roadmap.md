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

## v0.4 — deeper language and framework semantics ✅
- Function-scoped deterministic JavaScript/TypeScript and Go adapters while preserving a zero-runtime-dependency core.
- Java Spring discovery for `@Value`, `Environment.getProperty`, `@ConfigurationProperties` and common feature-flag calls.
- .NET/C# discovery for environment variables, `IConfiguration`, `GetValue` defaults and feature flags.
- JSON Schema finite-domain/default/validator extraction.
- Terraform bool and finite validation-domain extraction.
- Changed-line PR dependency slicing with file-level fallback only where line provenance is unavailable.
- Root-level test-name detection for Go, Java, .NET, Python and JS/TS conventions.

## v0.5 — deterministic testing guidance ✅
- `configreach plan` for bounded deterministic 1-wise, 2-wise and 3-wise configuration planning.
- Greedy covering-array style selection with deterministic lexicographic tie-breaking.
- Existing test-scenario evidence removed from the required interaction set before planning.
- CPU-safety bounds for domain size, interaction count and generated case count.
- Sensitive-looking configuration excluded from suggested assignments.
- Structured JSON fixture suggestions plus text and Markdown renderers.
- Single-key missing finite values remain actionable even when no multi-key dependency scope is available.

## v0.6 — scale and ecosystem depth
- Workspace-local incremental cache invalidation for very large monorepos.
- Richer framework validator-domain extraction.
- Optional parser-backed external adapters while keeping the core dependency-free.
- Additional deterministic fixture exporters for popular test frameworks.

## v1.0
- Stable report and planning schemas.
- Stable plugin contract.
- Versioned adapter capability matrix.
- Reproducibility suite across operating systems and supported Python versions.
