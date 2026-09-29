# Custom feature-flag provider adapter example

This directory demonstrates that Adapter API v1 is not limited to programming-language parsers. It adds a deterministic provider for local `.featureflags` files.

Example input:

```text
CHECKOUT_V2=false|true
PAYMENT_MODE=sandbox|live
```

The adapter records each key as a feature-flag declaration and treats the pipe-separated values as a finite domain.

```bash
python -m pip install -e .
python -m pip install -e examples/plugins/feature_flags_provider
configreach adapters
configreach scan path/to/repository
```

The provider uses only ConfigReach core and the Python standard library; it performs no network access and executes no target code.
