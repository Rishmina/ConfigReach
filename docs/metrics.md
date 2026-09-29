# Metrics

## Key coverage

A key is covered when ConfigReach finds test evidence for it or when an opt-in trace observes it while executing the supplied test command.

`covered configuration keys / effective configuration keys`

Keys present in the baseline remain visible but are excluded from the effective denominator.

## Value coverage

ConfigReach reports value coverage only when an expected value domain is explicitly knowable. Current Python sources include comparisons, argparse choices, `Literal[...]`, Enum-backed settings, bool annotations and feature flags. Unknown domains are not assigned fabricated percentages.

## Boolean, enum and branch-state coverage

Boolean coverage measures explicit `true`/`false` states. Enum coverage excludes pure booleans and measures known discrete domains. Branch-state coverage uses values found in configuration-dependent branches and checks which of those values appear in explicit test-value evidence. Branch source locations are retained in the report.

## Pairwise key coverage

ConfigReach creates interaction pairs from dependency scopes. Python AST reads are scoped to the function that reads them; other language adapters conservatively use file scope. A key pair is covered when both keys have evidence in the same detected test file.

This avoids treating two settings used in unrelated Python functions as an interaction merely because they share a source file.

## Pairwise value-state coverage

When both keys in an interaction pair have finite known domains, ConfigReach builds the bounded pairwise value state space. It then checks explicit test-value observations that occur in the same test scenario (`path::test_function` for Python, file scope for conservative adapters).

Example: if `FEATURE_A={true,false}` and `MODE={sandbox,live}`, there are four known pairwise states. Tests that explicitly exercise `(true,sandbox)` and `(false,live)` cover 2/4 = 50%. Domains with more than 256 Cartesian pair states are not expanded.

This metric is deterministic and evidence-based; it does not claim that unknown or semantically impossible combinations are testable.

## Blast radius

A key's blast radius is the count of distinct application source files and top-level modules that read it. PR reports show both counts and compare the merge-base snapshot with the current tree.
