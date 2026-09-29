# Deterministic fixture exporters

ConfigReach can turn a deterministic test plan into lightweight fixture scaffolding for common test ecosystems. The exporters consume only the already-computed `TestPlan`; they do not call a model, invent values, execute target code, or synthesize assertions.

```bash
configreach plan . --fixture pytest --output test_configreach_cases.py
configreach plan . --fixture jest --output configreach.cases.ts
configreach plan . --fixture go --output configreach_cases_test.go
configreach plan . --fixture shell --output configreach_cases.sh
configreach plan . --fixture junit --output ConfigReachCases.java
configreach plan . --fixture xunit --output ConfigReachCases.cs
```

Supported exporters:

- `pytest` — a parametrized `configreach_env` fixture using `monkeypatch.setenv`.
- `jest` — an exported case array plus a small `process.env` application helper.
- `go` — a deterministic `[]Case` table containing environment maps.
- `shell` — one clearly separated group of `export` statements per suggested case.
- `junit` — a JUnit 5 `Stream<Arguments>` source using immutable environment maps.
- `xunit` — a .NET `IEnumerable<object[]>` MemberData-compatible source plus an environment application helper.

The generated scaffolds intentionally contain no business assertions. A ConfigReach case means that a known configuration state closes one or more coverage gaps; it does not tell ConfigReach what the correct application outcome should be.

Sensitive-looking keys are excluded upstream by the planner, so fixture exporters never require real password, token, secret, private-key, credential, or API-key values.
