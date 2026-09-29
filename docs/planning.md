# Deterministic test planning

`configreach plan` converts already-discovered finite configuration domains into a bounded test plan. It does not execute target code, call a model, invent values, or generate test source code.

## Examples

```bash
configreach plan .
configreach plan . --strength 3 --max-cases 40
configreach plan . --format json --output configreach-plan.json
configreach plan examples/combinations --format markdown
```

The planner supports 1-wise, 2-wise, and 3-wise interaction strength. It starts from ConfigReach dependency scopes, known finite domains, and explicit test-value observations. Interactions already observed together in the same detected test scenario are removed before planning.

## Bounded greedy algorithm

For each eligible dependency scope, ConfigReach:

1. keeps only non-sensitive keys with known finite domains,
2. enumerates required N-wise value interactions up to the configured interaction cap,
3. subtracts interactions already observed in tests,
4. creates deterministic candidate assignments using only known values,
5. greedily chooses the assignment covering the largest number of remaining interactions,
6. applies lexicographic tie-breaking so repeated runs are reproducible,
7. stops at `--max-cases`.

The defaults are deliberately conservative:

- `--strength 2`
- `--max-cases 64`
- `--max-domain 12`
- `--max-interactions 20000`

Scopes that exceed the limits are reported as warnings instead of causing a Cartesian-product explosion.

## Sensitive configuration

Keys whose names look sensitive, such as passwords, secrets, API keys, tokens, private keys, and credentials, are excluded from planned assignments. The planner is not a secret-management tool and never needs real credential values.

## Structured fixture suggestions

JSON output is intended for downstream tooling:

```json
{
  "schema_version": 1,
  "strength": 2,
  "cases": [
    {
      "id": "CRP001",
      "scope": "payment.py::handle",
      "configuration": {
        "PAYMENT_MODE": "live",
        "REGION": "eu"
      },
      "covers": [
        "PAYMENT_MODE=live & REGION=eu"
      ]
    }
  ]
}
```

This is structured deterministic data, not generated prose. A test framework integration can consume the JSON and decide how to materialize fixtures locally.

## Limits

A suggested case means “this known configuration state would close one or more observed coverage gaps.” It does not prove the application is semantically correct for that state, and ConfigReach intentionally does not synthesize assertions or expected business outcomes.
