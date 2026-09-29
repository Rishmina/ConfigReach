# Architecture

ConfigReach separates **discovery**, **coverage evidence**, **policy**, and **reporting** so every result remains inspectable and reproducible.

1. `discover.py` walks eligible repository files using explicit ignore rules and a size cap.
2. Python source is parsed with `ast`; selected cross-language idioms use conservative deterministic patterns.
3. Built-in declaration adapters inspect dotenv templates, JSON, TOML, INI/CFG, properties, YAML, Dockerfiles, Terraform, Makefiles, Helm values, Pydantic settings and GitHub Actions variable/secret references.
4. Test files contribute key-level evidence and, when assignments are statically visible, value-level evidence.
5. Optional runtime tracing records configuration key names and value fingerprints only; raw runtime values are not persisted.
6. `models.py` stores read/declaration/test/branch provenance, known values, validators, function-scoped dependency information, explicit test-value scenarios, blast radius and deterministic findings.
7. `baseline.py` suppresses legacy uncovered keys from CI gating without removing them from the report.
8. `cache.py` caches the deterministic scan model using repository-file metadata fingerprints. Cache state is not part of machine-readable result semantics.
9. `plugins.py` loads third-party adapters through the `configreach.adapters` Python entry-point group. Plugin failures become scanner warnings rather than crashing the core.
10. `reporters.py` renders the same model as text, JSON, Markdown, SARIF or a standalone searchable HTML graph.

## Coverage model

ConfigReach deliberately exposes multiple metrics instead of collapsing everything into an opaque score:

- **Key coverage**: discovered configuration inputs with detected test or runtime evidence / effective discovered inputs.
- **Value coverage**: statically observed tested values / explicitly known expected values.
- **Boolean coverage**: tested true/false states / known boolean states.
- **Pairwise key coverage**: configuration key pairs read from the same dependency scope (Python function when available, otherwise file) that also have joint test evidence.
- **Pairwise value-state coverage**: explicitly known value pairs for interacting keys that are observed together in the same detected test scenario.

Combination metrics are bounded and conservative. Unknown domains remain unknown; large domains are not blindly expanded.

## Monorepos

Package roots are detected from `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, Maven and Gradle manifests. The report exposes these roots and keeps source paths intact so downstream tooling can group findings per package. Cross-package incremental invalidation is a future optimization; the current persistent cache invalidates the repository scan when eligible file metadata changes.

## Determinism rules

- No network calls, model inference or telemetry in the core.
- Files are processed in normalized sorted path order.
- Machine-readable outputs exclude timing and cache-hit metadata.
- Unknown configuration semantics remain unknown instead of being guessed.
- Sensitive-looking values are redacted before they enter report serialization.
