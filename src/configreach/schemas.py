from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


REPORT_SCHEMA_VERSION = 5
WORKSPACE_SCHEMA_VERSION = 1
PLAN_SCHEMA_VERSION = 1
REPRODUCIBILITY_SCHEMA_VERSION = 1
CAPABILITY_SCHEMA_VERSION = 1
SCHEMA_REGISTRY_VERSION = 1


@dataclass(frozen=True)
class SchemaSpec:
    kind: str
    current_version: int
    min_supported_version: int
    required_top_level: tuple[str, ...]
    required_summary: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_top_level"] = list(self.required_top_level)
        data["required_summary"] = list(self.required_summary)
        return data


SCHEMAS: dict[str, SchemaSpec] = {
    "report": SchemaSpec(
        "report",
        REPORT_SCHEMA_VERSION,
        3,
        ("schema_version", "root", "summary", "keys", "findings", "warnings"),
        (
            "files_scanned",
            "tests_scanned",
            "configuration_inputs",
            "covered_inputs",
            "uncovered_inputs",
            "coverage",
        ),
        "Report schemas 3-5 are accepted for structural compatibility checks; new output is always v5.",
    ),
    "workspace": SchemaSpec(
        "workspace",
        WORKSPACE_SCHEMA_VERSION,
        1,
        ("schema_version", "root", "summary", "workspaces"),
        ("workspaces", "configuration_inputs", "covered_inputs", "coverage"),
    ),
    "plan": SchemaSpec(
        "plan",
        PLAN_SCHEMA_VERSION,
        1,
        ("schema_version", "strength", "summary", "missing_values", "cases", "warnings"),
        ("cases", "interactions_total", "interactions_already_covered", "interactions_remaining"),
    ),
    "reproducibility": SchemaSpec(
        "reproducibility",
        REPRODUCIBILITY_SCHEMA_VERSION,
        1,
        ("schema_version", "reproducible", "runs"),
    ),
    "capabilities": SchemaSpec(
        "capabilities",
        CAPABILITY_SCHEMA_VERSION,
        1,
        ("schema_version", "builtins"),
    ),
}


@dataclass(frozen=True)
class SchemaValidation:
    kind: str
    schema_version: int | None
    current_version: int
    min_supported_version: int
    compatible: bool
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["errors"] = list(self.errors)
        data["warnings"] = list(self.warnings)
        return data


def schema_registry_document() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_REGISTRY_VERSION,
        "schemas": {name: spec.to_dict() for name, spec in sorted(SCHEMAS.items())},
    }


def validate_document(kind: str, data: Any) -> SchemaValidation:
    if kind not in SCHEMAS:
        raise ValueError(f"unsupported schema kind: {kind}")
    spec = SCHEMAS[kind]
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return SchemaValidation(
            kind,
            None,
            spec.current_version,
            spec.min_supported_version,
            False,
            "invalid",
            ("document must be a JSON object",),
            (),
        )

    raw_version = data.get("schema_version")
    version: int | None
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        version = None
        errors.append("schema_version must be an integer")
    else:
        version = raw_version
        if version > spec.current_version:
            errors.append(
                f"schema version {version} is newer than supported version {spec.current_version}"
            )
        elif version < spec.min_supported_version:
            errors.append(
                f"schema version {version} is older than minimum supported version {spec.min_supported_version}"
            )
        elif version < spec.current_version:
            warnings.append(
                f"legacy schema version {version} is accepted; current version is {spec.current_version}"
            )

    for name in spec.required_top_level:
        if name not in data:
            errors.append(f"missing required field: {name}")

    if spec.required_summary:
        summary = data.get("summary")
        if not isinstance(summary, dict):
            errors.append("summary must be an object")
        else:
            for name in spec.required_summary:
                if name not in summary:
                    errors.append(f"missing required summary field: {name}")

    # Stable container-shape checks catch accidental breaking changes without
    # requiring a third-party JSON Schema runtime in the core package.
    list_fields = {
        "report": ("keys", "findings", "warnings"),
        "workspace": ("workspaces",),
        "plan": ("cases", "warnings"),
        "reproducibility": ("runs",),
        "capabilities": ("builtins",),
    }[kind]
    for name in list_fields:
        if name in data and not isinstance(data[name], list):
            errors.append(f"{name} must be an array")

    if kind == "plan" and "missing_values" in data and not isinstance(data["missing_values"], dict):
        errors.append("missing_values must be an object")
    if kind == "reproducibility" and "reproducible" in data and not isinstance(data["reproducible"], bool):
        errors.append("reproducible must be a boolean")

    compatible = not errors
    if errors:
        status = "invalid"
    elif version is not None and version < spec.current_version:
        status = "compatible-legacy"
    else:
        status = "current"
    return SchemaValidation(
        kind,
        version,
        spec.current_version,
        spec.min_supported_version,
        compatible,
        status,
        tuple(errors),
        tuple(warnings),
    )
