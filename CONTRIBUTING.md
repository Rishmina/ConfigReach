# Contributing

ConfigReach aims to make configuration coverage measurable with deterministic, inspectable rules.

1. Fork the repository and create a focused branch.
2. Install with `python -m pip install -e ".[dev]"`.
3. Add tests for every detector or behavior change.
4. Run `pytest` and `configreach scan examples/basic`.
5. Open a pull request explaining false-positive/false-negative tradeoffs.

New language adapters should include small fixtures showing both reads and tests. Core analysis must remain usable without network access, an LLM, telemetry, or a paid service.
