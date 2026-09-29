# Reproducibility verification

ConfigReach machine-readable analysis is designed to be deterministic for the same repository state and configuration.

```bash
configreach reproduce .
configreach reproduce . --runs 5
configreach reproduce . --runs 3 --format json --output repro.json
```

The command performs repeated **uncached** scans, canonicalizes the report, and computes SHA-256 digests. It exits `0` only when every digest matches. Absolute repository roots, timing and cache metadata are excluded because they are execution-environment metadata rather than configuration-coverage semantics.

Example:

```text
ConfigReach reproducibility: PASS
run 1: 9b...e4
run 2: 9b...e4
run 3: 9b...e4
```

## Cross-platform CI

The repository includes `.github/workflows/reproducibility.yml`. It runs the same fixture on Ubuntu, macOS and Windows, uploads one canonical digest per operating system, then fails a comparison job if the three digests differ.

This checks both repeatability on each runner and equality of the canonical machine result across supported operating systems.

## Scope

Reproducibility applies to ConfigReach's own deterministic scanner and deterministic plugins. Plugins declaring `deterministic = false` are rejected by adapter API v1. Runtime tracing records observations from the command the user chooses to execute; naturally, a nondeterministic target test process may produce different trace evidence.
