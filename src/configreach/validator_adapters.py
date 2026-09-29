from __future__ import annotations

import re

from .models import ConfigKey, Location, is_sensitive


def _safe_value(name: str, value: object) -> str:
    if is_sensitive(name):
        return "<set>"
    text = str(value)
    return text if len(text) <= 120 else text[:117] + "..."


def record_zod(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    """Extract finite domains and validators from common one-line Zod object fields."""
    field = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(z\..*?)(?:,\s*)?$")
    enum = re.compile(r"z\.enum\(\s*\[([^\]]*)\]")
    literal = re.compile(r"z\.literal\(\s*(['\"])(.*?)\1\s*\)")
    default = re.compile(r"\.default\(\s*(['\"])(.*?)\1\s*\)")
    for lineno, line in enumerate(text.splitlines(), 1):
        match = field.match(line)
        if not match:
            continue
        name, expr = match.groups()
        key = keys.setdefault(name, ConfigKey(name=name))
        key.languages.add("javascript")
        key.categories.update({"settings", "zod"})
        key.declarations.append(Location(rel, lineno, "declaration", "zod"))
        if "z.boolean(" in expr or expr.startswith("z.boolean"):
            key.expected_values.update({"true", "false"})
            key.validators.add("zod:boolean")
        enum_match = enum.search(expr)
        if enum_match:
            for value in re.findall(r"['\"]([^'\"]+)['\"]", enum_match.group(1)):
                key.expected_values.add(_safe_value(name, value))
            key.validators.add("zod:enum")
        literal_match = literal.search(expr)
        if literal_match:
            key.expected_values.add(_safe_value(name, literal_match.group(2)))
            key.validators.add("zod:literal")
        default_match = default.search(expr)
        if default_match:
            key.defaults.add(_safe_value(name, default_match.group(2)))
        for validator, pattern in (
            ("min", r"\.min\(\s*([^\)]+)\)"),
            ("max", r"\.max\(\s*([^\)]+)\)"),
            ("regex", r"\.regex\(\s*(/[^/]+/[a-z]*)\s*\)"),
            ("url", r"\.url\(\s*\)"),
            ("email", r"\.email\(\s*\)"),
            ("nonempty", r"\.nonempty\(\s*\)"),
        ):
            found = re.search(pattern, expr)
            if found:
                detail = found.group(1) if found.groups() else "true"
                key.validators.add(f"zod:{validator}={detail}")


def record_java_bean_validation(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    """Attach Bean Validation annotations to Spring @Value-backed configuration keys."""
    block = re.compile(
        r"(?P<annotations>(?:\s*@(?:Min|Max|Positive|PositiveOrZero|Negative|NegativeOrZero|Size|Pattern|NotBlank|NotNull|Value)\s*(?:\([^\n]*\))?\s*\n?)+)"
        r"\s*(?:private|protected|public)\s+[A-Za-z0-9_<>, ?\[\].]+\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:=[^;]+)?;",
        re.M,
    )
    value_pat = re.compile(r"@Value\(\s*['\"]\$\{([^}:]+)(?::([^}]*))?\}['\"]\s*\)")
    validators = {
        "Min": re.compile(r"@Min\(\s*([^\)]+)\)"),
        "Max": re.compile(r"@Max\(\s*([^\)]+)\)"),
        "Size": re.compile(r"@Size\(\s*([^\)]*)\)"),
        "Pattern": re.compile(r"@Pattern\(\s*regexp\s*=\s*['\"]([^'\"]*)['\"]"),
        "Positive": re.compile(r"@Positive\b"),
        "PositiveOrZero": re.compile(r"@PositiveOrZero\b"),
        "Negative": re.compile(r"@Negative\b"),
        "NegativeOrZero": re.compile(r"@NegativeOrZero\b"),
        "NotBlank": re.compile(r"@NotBlank\b"),
        "NotNull": re.compile(r"@NotNull\b"),
    }
    for match in block.finditer(text):
        annotations = match.group("annotations")
        value_match = value_pat.search(annotations)
        if not value_match:
            continue
        name = value_match.group(1)
        key = keys.setdefault(name, ConfigKey(name=name))
        key.languages.add("java")
        key.categories.add("spring")
        line = text.count("\n", 0, match.start()) + 1
        for label, pattern in validators.items():
            found = pattern.search(annotations)
            if found:
                value = found.group(1) if found.groups() else "true"
                key.validators.add(f"java:{label}={value}")
        if not any(loc.path == rel and loc.line == line for loc in key.declarations):
            key.declarations.append(Location(rel, line, "declaration", "java:bean-validation"))


def record_extended_json_schema(data: object, rel: str, keys: dict[str, ConfigKey]) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("properties"), dict):
        return

    def walk(properties: dict[str, object], prefix: str = "") -> None:
        for raw_name, spec in properties.items():
            if not isinstance(spec, dict):
                continue
            name = f"{prefix}.{raw_name}" if prefix else str(raw_name)
            key = keys.setdefault(name, ConfigKey(name=name))
            for validator in (
                "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minItems", "maxItems",
                "minProperties", "maxProperties", "format",
            ):
                if validator in spec:
                    key.validators.add(f"json-schema:{validator}={spec[validator]}")
            for branch_name in ("oneOf", "anyOf"):
                branches = spec.get(branch_name)
                if not isinstance(branches, list):
                    continue
                finite: set[str] = set()
                for branch in branches:
                    if not isinstance(branch, dict):
                        continue
                    if "const" in branch:
                        finite.add(_safe_value(name, branch["const"]))
                    values = branch.get("enum")
                    if isinstance(values, list):
                        finite.update(_safe_value(name, value) for value in values)
                if finite:
                    key.expected_values.update(finite)
                    key.validators.add(f"json-schema:{branch_name}-finite-domain")
            nested = spec.get("properties")
            if isinstance(nested, dict):
                walk(nested, name)

    walk(data["properties"])


def record_terraform_validators(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    for match in re.finditer(r'variable\s+"([A-Za-z_][A-Za-z0-9_-]*)"\s*\{(?P<body>.*?)\n\}', text, re.S):
        name = match.group(1)
        body = match.group("body")
        key = keys.setdefault(name, ConfigKey(name=name))
        if re.search(r"regex\(\s*['\"]([^'\"]+)['\"]\s*,\s*var\." + re.escape(name), body):
            key.validators.add("terraform:regex")
        for operator, label in ((">=", "ge"), (">", "gt"), ("<=", "le"), ("<", "lt")):
            numeric = re.search(r"var\." + re.escape(name) + r"\s*" + re.escape(operator) + r"\s*(-?\d+(?:\.\d+)?)", body)
            if numeric:
                key.validators.add(f"terraform:{label}={numeric.group(1)}")
        length = re.search(r"length\(\s*var\." + re.escape(name) + r"\s*\)\s*(>=|>|<=|<)\s*(\d+)", body)
        if length:
            key.validators.add(f"terraform:length{length.group(1)}{length.group(2)}")
