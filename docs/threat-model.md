# Threat model and privacy

ConfigReach is intended to run against source repositories that the operator is authorized to inspect.

## Assets

Potentially sensitive assets include source code, environment-variable names, configuration defaults, test fixtures and runtime configuration values.

## Protections

- Static scanning is local and performs no network requests.
- There is no telemetry.
- Keys that look secret-bearing are marked sensitive and their static values are redacted in reports.
- Python dynamic tracing records only a short SHA-256-derived fingerprint of each observed value, sufficient to distinguish states without writing the value itself.
- The default ignore list excludes common dependency, VCS, build and cache directories.

## Limitations

A configuration key name itself can be sensitive. Generated JSON/SARIF/Markdown reports should be treated as repository-derived artifacts and shared according to the repository's own access policy. Regex adapters may produce false positives; dynamic tracing executes the command supplied by the user and therefore inherits that command's security properties.
