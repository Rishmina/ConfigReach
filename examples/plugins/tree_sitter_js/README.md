# Optional tree-sitter JavaScript adapter example

This directory demonstrates how parser-backed adapters stay separate from ConfigReach's zero-runtime-dependency core.

```bash
python -m pip install -e ./examples/plugins/tree_sitter_js
configreach adapters
configreach scan path/to/javascript/project
```

The example registers itself through the `configreach.adapters` entry-point group, declares adapter API version 1, and uses `tree-sitter-javascript` to locate `process.env.KEY` syntax-tree nodes with exact line provenance.

It is intentionally optional. Installing base `configreach` does not install tree-sitter or any parser package.
