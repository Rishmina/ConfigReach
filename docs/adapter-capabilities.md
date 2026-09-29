# Built-in adapter capability matrix

ConfigReach intentionally separates **semantic** adapters from conservative pattern adapters. This table describes what the zero-runtime-dependency core can establish today.

| Ecosystem | Reads | Function scope | Defaults | Finite domains / branches | Test values | Framework support |
|---|---|---:|---:|---:|---:|---|
| Python | AST | yes | yes | `Literal`, Enum, bool, comparisons | yes | Pydantic Settings, argparse, Click/Typer patterns |
| JavaScript / TypeScript | deterministic lexical adapter | yes | `??` / `||` env defaults | direct and bound-variable comparisons | `process.env` assignments | LaunchDarkly/Unleash-style boolean flag calls |
| Go | deterministic lexical adapter | yes | — | direct and bound-variable comparisons | `t.Setenv` / `os.Setenv` | standard library env APIs |
| Java | deterministic adapter | file | selected property defaults | bool configuration-property fields | name evidence | Spring `@Value`, `Environment.getProperty`, `@ConfigurationProperties`, flag calls |
| .NET / C# | deterministic adapter | file | `GetValue` defaults | boolean feature flags | `SetEnvironmentVariable` | `IConfiguration`, environment variables, `IFeatureManager`-style calls |
| Rust | deterministic pattern | file | — | — | name evidence | `env::var`, `env::var_os` |
| Ruby | deterministic pattern | file | — | — | name evidence | `ENV[...]`, `ENV.fetch` |
| PHP | deterministic pattern | file | — | — | name evidence | `getenv`, common `env(...)` form |
| Shell | deterministic pattern | file | — | — | name evidence | `$VAR`, `${VAR}` |

## Configuration formats

The core also recognizes dotenv templates, JSON, TOML, INI/CFG, Java properties, YAML, Dockerfiles/Containerfiles, Docker Compose, Kubernetes-style environment declarations, Helm values, GitHub Actions vars/secrets, Terraform variables, Makefiles and JSON Schema property domains.

JSON Schema extraction understands `enum`, `const`, boolean types, defaults and selected validators. Terraform extraction understands boolean variables plus finite domains expressed through `contains([...], var.name)` and direct validation comparisons.

## Accuracy contract

“Semantic” here means ConfigReach tracks a language-level dependency scope and selected value relations. It does **not** claim compiler equivalence. Dynamic key construction, reflection, generated code, aliases hidden behind arbitrary helper functions and framework behavior that requires executing user code remain intentionally unknown unless an external adapter provides that evidence.
