from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .schemas import CAPABILITY_SCHEMA_VERSION


@dataclass(frozen=True)
class AdapterCapability:
    adapter_id: str
    ecosystem: str
    mode: str
    sources: tuple[str, ...]
    function_scope: bool = False
    finite_domains: bool = False
    validators: bool = False
    test_values: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sources"] = list(self.sources)
        return data


BUILTIN_CAPABILITIES: tuple[AdapterCapability, ...] = (
    AdapterCapability(
        "python-ast", "Python", "ast", ("os.getenv", "os.environ", "Pydantic", "argparse"),
        function_scope=True, finite_domains=True, validators=True, test_values=True,
        notes="Deepest built-in semantic adapter.",
    ),
    AdapterCapability(
        "javascript-semantic", "JavaScript/TypeScript", "deterministic-semantic",
        ("process.env", "Deno.env", "Bun.env", "feature flags"),
        function_scope=True, finite_domains=True, test_values=True,
    ),
    AdapterCapability(
        "zod-validator", "JavaScript/TypeScript", "deterministic-validator", ("Zod",),
        finite_domains=True, validators=True,
    ),
    AdapterCapability(
        "go-semantic", "Go", "deterministic-semantic", ("os.Getenv", "os.LookupEnv", "t.Setenv"),
        function_scope=True, finite_domains=True, test_values=True,
    ),
    AdapterCapability(
        "java-spring", "Java/Kotlin", "deterministic-semantic",
        ("System.getenv", "System.getProperty", "Spring @Value", "ConfigurationProperties", "Bean Validation"),
        finite_domains=True, validators=True,
    ),
    AdapterCapability(
        "dotnet", ".NET/C#", "deterministic-semantic",
        ("Environment", "IConfiguration", "GetValue", "feature flags"),
        finite_domains=True, test_values=True,
    ),
    AdapterCapability(
        "rust-pattern", "Rust", "deterministic-pattern", ("env::var", "env::var_os"),
    ),
    AdapterCapability(
        "ruby-pattern", "Ruby", "deterministic-pattern", ("ENV[]", "ENV.fetch"),
    ),
    AdapterCapability(
        "php-pattern", "PHP", "deterministic-pattern", ("getenv", "env"),
    ),
    AdapterCapability(
        "shell-pattern", "Shell", "deterministic-pattern", ("$VAR", "${VAR}"),
    ),
    AdapterCapability(
        "structured-config", "Config/deployment", "deterministic-structured",
        ("dotenv", "JSON", "TOML", "INI", "properties", "YAML", "Docker", "Kubernetes", "Helm", "GitHub Actions", "Make", "Terraform", "JSON Schema"),
        finite_domains=True, validators=True,
    ),
)


def builtin_capability_document() -> dict[str, Any]:
    return {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "builtins": [item.to_dict() for item in BUILTIN_CAPABILITIES],
    }
