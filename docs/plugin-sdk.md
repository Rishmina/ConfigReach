# Adapter plugin SDK

ConfigReach loads external deterministic adapters through the `configreach.adapters` Python entry-point group without making those adapters dependencies of the core package.

## Adapter API version 1

```python
class MyAdapter:
    name = "my-framework"
    api_version = 1
    parser = "my-parser"          # or "unspecified"
    deterministic = True
    capabilities = ("env-read", "finite-domain")

    def supports(self, path):
        return path.suffix == ".custom"

    def scan(self, *, path, rel, text, is_test, keys):
        # Add or update ConfigKey objects in `keys`.
        ...
```

Register it in the plugin package:

```toml
[project.entry-points."configreach.adapters"]
my-framework = "my_package.adapter:MyAdapter"
```

`api_version` defaults to `1` for backward compatibility with the early alpha protocol. New plugins should declare it explicitly. ConfigReach rejects unsupported API versions and adapters that declare `deterministic = false`.

## Diagnostics

```bash
configreach adapters
configreach adapters --format json
```

The command reports the core adapter API version, the versioned built-in capability matrix, installed plugin parser identities and declared capabilities, plus any load errors. A broken optional plugin does not crash core scanning.

## Optional parser-backed adapters

Parser packages remain outside the base install. See [`examples/plugins/tree_sitter_js`](../examples/plugins/tree_sitter_js/) for an example package that depends on `tree-sitter` and `tree-sitter-javascript`, registers through the adapter entry-point group, and reports exact JavaScript `process.env.KEY` syntax-tree locations.

Installing base `configreach` still installs no parser packages and no runtime dependencies.

## Safety and determinism requirements

Adapters should be pure local analyzers: no network requests, model calls, telemetry, subprocess execution of target application code, or nondeterministic sampling. Exceptions are isolated and surfaced as warnings with plugin identity.
