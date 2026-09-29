# Threat model and privacy

ConfigReach is intended to run against source repositories that the operator is authorized to inspect.

## Assets

Potentially sensitive assets include source code, environment-variable names, configuration defaults, test fixtures and runtime configuration values.

## Protections

- Static scanning is local and performs no network requests.
- There is no telemetry, LLM, hosted API or paid-service dependency.
- Keys that look secret-bearing are marked sensitive and static values are redacted before report serialization.
- Python dynamic tracing records only a short SHA-256-derived fingerprint of each observed value, sufficient to distinguish states without writing the raw value itself.
- The default ignore list excludes common dependency, VCS, build and `.configreach` artifact directories.
- The persistent cache contains the already-redacted report model, not raw source contents.
- Optional third-party adapters are isolated from the core error path: adapter failures are warnings. Installing a plugin nevertheless means trusting that package with normal Python-process permissions.

## Findings are not secret scanning

`CR005` detects a sensitive-looking configuration name with a non-empty static default. It is a configuration-safety signal, not a credential validity test and not a substitute for a dedicated secret scanner.

## Dynamic tracing

Tracing executes exactly the Python command supplied by the user and therefore inherits that command's security properties. ConfigReach does not sandbox target tests or application code.

## Generated reports

Configuration key names can themselves reveal architecture. JSON, SARIF, Markdown and HTML reports should be handled according to the repository's own access policy.
