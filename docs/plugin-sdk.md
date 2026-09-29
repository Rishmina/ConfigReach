# Adapter plugin SDK

ConfigReach can load external deterministic adapters without making them dependencies of the core package.

A plugin implements two methods:

```python
class MyAdapter:
    name = "my-framework"

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

Adapters must be deterministic and should not perform network requests. ConfigReach catches adapter exceptions and emits a scanner warning so one optional plugin cannot make the core analyzer unusable.

The public protocol is currently alpha. A stable compatibility contract is planned before ConfigReach 1.0.
