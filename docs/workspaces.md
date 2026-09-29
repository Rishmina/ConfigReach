# Workspace-local scanning

`configreach workspace` is the monorepo-oriented execution mode. It detects package roots from local manifests and scans each workspace with an independent ConfigReach cache boundary.

```bash
configreach workspace .
configreach workspace . --format json --output workspaces.json
configreach workspace . --format markdown
```

Recognized workspace markers include `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `build.gradle.kts`, and `.csproj` files.

## Incremental invalidation

Each detected workspace is scanned from its own root, so the normal `.configreach/cache/` file belongs to that workspace. A parent workspace automatically ignores nested workspace directories during its own scan, preventing double counting.

If a monorepo contains `packages/payments` and `packages/risk`, and only `packages/payments` changes, the next workspace scan can reuse the warmed `packages/risk` cache while invalidating only the payments cache.

This is deliberately deterministic and local. ConfigReach does not require a remote cache service, daemon, telemetry endpoint, or repository index server.

## Output

The workspace report includes per-workspace key coverage, input count, file/test counts, finding count, and whether that workspace was served from cache. The aggregate coverage is weighted by discovered configuration inputs rather than averaging percentages.

## Boundaries

Workspace mode is an execution optimization and reporting view, not a new semantic model. Cross-workspace runtime interactions are not inferred unless they also appear in a normal repository-level scan. Use ordinary `configreach scan .` when a single combined repository model is more important than incremental monorepo execution.
