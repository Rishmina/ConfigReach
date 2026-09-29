# Optional tree-sitter Go adapter example

This directory demonstrates a parser-backed **Adapter API v1** plugin without adding tree-sitter to ConfigReach core.

The adapter parses Go syntax trees and records literal `os.Getenv("KEY")` and `os.LookupEnv("KEY")` reads with source-line provenance.

```bash
python -m pip install -e .
python -m pip install -e examples/plugins/tree_sitter_go
configreach adapters
configreach scan path/to/go/repository
```

The example declares `deterministic = True`, `api_version = 1`, parser identity and capability metadata. Its dependencies are isolated to the optional plugin package; installing ConfigReach itself still installs no runtime dependencies.
