# Machine-readable schema compatibility

ConfigReach exposes versioned JSON contracts for reports, workspace scans, deterministic test plans, reproducibility results and adapter capability inventories.

Inspect the registry:

```bash
configreach schema
configreach schema --format json
```

Validate an artifact before consuming it:

```bash
configreach schema --kind report --check configreach.json
configreach schema --kind workspace --check workspaces.json --format json
```

A compatible document exits `0`. A structurally incompatible, too-old or future document exits `1`. CLI/JSON/file errors exit `2`.

## Current compatibility matrix

| Artifact | Current | Minimum supported |
|---|---:|---:|
| scan report | 5 | 3 |
| workspace report | 1 | 1 |
| deterministic plan | 1 | 1 |
| reproducibility result | 1 | 1 |
| adapter capability inventory | 1 | 1 |

Report schemas 3 and 4 are treated as **compatible legacy inputs** for structural inspection. ConfigReach always emits the current report schema. Future schema versions are rejected rather than guessed.

## Compatibility policy

Before v1.0, ConfigReach may add optional fields to a current schema without incrementing the version. Removing or renaming an existing documented field, changing its container type, or changing its meaning requires a schema-version change.

The compatibility validator intentionally uses the Python standard library instead of a JSON Schema dependency. It checks schema-version ranges, required stable fields and stable container shapes. It does not claim to validate every nested value semantically.

Golden fixtures live under `tests/fixtures/schemas/` and are exercised by CI. They make accidental breaking changes visible during development.

## Migration guidance

Consumers should:

1. Read `schema_version` first.
2. Reject versions newer than the consumer understands.
3. Treat missing optional fields as unknown rather than false/zero.
4. Prefer named fields over positional assumptions.
5. Preserve unknown fields when proxying or storing artifacts.

For reports, versions 3-5 can be read structurally by ConfigReach v0.8. New output is version 5. No automatic destructive rewrite is performed because doing so could invent semantic evidence that did not exist in an older report.
