# Metrics

## Key coverage

A key is covered when ConfigReach finds test evidence for it or when an opt-in trace observes it while executing the supplied test command.

`covered configuration keys / effective configuration keys`

Keys present in the baseline remain visible but are excluded from the effective denominator.

## Value coverage

ConfigReach reports value coverage only when an expected value domain is explicitly knowable, for example:

- Python comparisons such as `os.getenv("MODE") == "live"`,
- argparse `choices`,
- boolean feature flags.

Unknown domains are not assigned fabricated percentages.

## Boolean coverage

When a key is identified as boolean, the known domain is `true` and `false`. The metric reports how many of those states appear in detected test-value evidence.

## Pairwise configuration-combination coverage

For every application source file that reads two or more configuration keys, ConfigReach creates key pairs. A pair is covered when both keys appear in the same detected test file. This catches a common gap where two individually-tested settings interact in application code but are never tested together.

This metric is intentionally conservative and does not imply full combinatorial testing of all values.

## Blast radius

A key's blast radius is the count of distinct application source files and top-level modules that read it. PR reports show this number to distinguish a local setting from configuration that changes behavior across many modules.
