# Security policy

## Reporting

Please report potential security vulnerabilities privately through GitHub's security advisory mechanism rather than a public issue.

## Data handling

The static analyzer reads files from the target repository and does not make network requests. Dynamic Python tracing stores configuration key names and SHA-256-derived value fingerprints; it does not intentionally persist raw runtime values. Sensitive-looking static defaults are redacted in report output.

ConfigReach is a developer-analysis tool, not a secrets manager or a substitute for a dedicated secret scanner.
