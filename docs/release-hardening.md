# Release hardening

ConfigReach v0.9 adds deterministic checks around the artifacts that would be published to a Python package index or attached to a GitHub release. These checks are development/release tooling only; the installed ConfigReach package still has zero runtime dependencies.

## Build twice and compare

```bash
python -m pip install -e ".[dev]"
python tools/release_repro.py --output release-repro.json --artifacts-dir dist
```

The harness sets a fixed `SOURCE_DATE_EPOCH`, `PYTHONHASHSEED=0` and UTC timezone, builds a wheel and source distribution twice in separate temporary directories, and compares:

- the exact SHA-256 of each artifact,
- a canonical SHA-256 of the files contained inside the wheel/sdist, ignoring archive timestamp/order metadata.

The release gate requires **exact byte reproducibility**. Canonical content comparison is retained as a diagnostic so a future packaging-tool change can distinguish container metadata drift from an actual content change.

## Inspect an existing release directory

```bash
configreach release dist
configreach release dist --format json --output release-manifest.json
```

Compare two prebuilt artifact directories:

```bash
configreach release dist-a --compare dist-b
```

`--allow-byte-differences` exists for diagnostics only; the repository release workflow does not use it.

## GitHub release gate

`.github/workflows/release-reproducibility.yml` performs the following on a GitHub-hosted CPU runner:

1. installs only the development build tools,
2. builds wheel and sdist twice,
3. requires exact artifact hashes to match,
4. writes a machine-readable release manifest,
5. force-installs the generated wheel without dependencies,
6. runs a ConfigReach smoke scan from that installed wheel,
7. uploads the wheel, sdist and reproducibility evidence as workflow artifacts.

No package upload or release publication happens automatically.

## Performance history

The Performance workflow produces `performance-history.json` with commit SHA, workflow run identifiers, runner OS, Python version, machine architecture and the synthetic polyglot budget result. GitHub retains each run's history artifact so regressions can be compared across commits without introducing telemetry or a hosted metrics service.
