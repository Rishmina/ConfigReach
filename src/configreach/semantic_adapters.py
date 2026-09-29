from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .models import ConfigKey, Location, is_sensitive


def _safe_value(name: str, value: object) -> str:
    if value is None:
        return "<none>"
    if is_sensitive(name):
        return "<set>"
    text = str(value)
    return text if len(text) <= 120 else text[:117] + "..."


def _item(keys: dict[str, ConfigKey], name: str, *, language: str, category: str) -> ConfigKey:
    key = keys.setdefault(name, ConfigKey(name=name))
    key.languages.add(language)
    key.categories.add(category)
    return key


def _quoted_value(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] in {'"', "'", '`'} and raw[-1] == raw[0]:
        raw = raw[1:-1]
    if raw in {"true", "false", "True", "False"}:
        return raw.lower()
    return raw


def _brace_counts(line: str) -> tuple[int, int]:
    """Count braces while ignoring quoted strings and line comments.

    This is deliberately a small deterministic lexer, not a language parser. It is
    sufficient for function-scope attribution without adding runtime dependencies.
    """
    opens = closes = 0
    quote: str | None = None
    escaped = False
    i = 0
    while i < len(line):
        ch = line[i]
        nxt = line[i + 1] if i + 1 < len(line) else ""
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in {'"', "'", '`'}:
            quote = ch
            i += 1
            continue
        if ch == "/" and nxt == "/":
            break
        if ch == "{":
            opens += 1
        elif ch == "}":
            closes += 1
        i += 1
    return opens, closes


def _iter_scoped_lines(text: str, language: str) -> Iterable[tuple[int, str, str]]:
    """Yield (line_no, line, scope) with lightweight function scope tracking."""
    js_function = re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>")
    js_method = re.compile(r"^\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{")
    go_function = re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(")

    depth = 0
    stack: list[tuple[str, int]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        while stack and depth < stack[-1][1]:
            stack.pop()

        name: str | None = None
        if language == "javascript":
            m = js_function.search(line)
            if m:
                name = m.group(1) or m.group(2)
            else:
                mm = js_method.search(line)
                if mm and mm.group(1) not in {"if", "for", "while", "switch", "catch"}:
                    name = mm.group(1)
        elif language == "go":
            m = go_function.search(line)
            if m:
                name = m.group(1)

        opens, closes = _brace_counts(line)
        scope = name or (stack[-1][0] if stack else "module")
        yield lineno, line, scope

        if name and opens > closes:
            stack.append((name, depth + 1))
        depth += opens - closes
        while stack and depth < stack[-1][1]:
            stack.pop()


def record_javascript_typescript(text: str, rel: str, is_test: bool, keys: dict[str, ConfigKey]) -> None:
    env_read = re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]*)|\[['\"]([A-Z][A-Z0-9_]*)['\"]\])")
    deno_read = re.compile(r"Deno\.env\.get\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]\s*\)")
    bun_read = re.compile(r"Bun\.env\.([A-Z][A-Z0-9_]*)")
    assignment = re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]*)|\[['\"]([A-Z][A-Z0-9_]*)['\"]\])\s*=\s*(['\"`][^'\"`]*['\"`]|true|false|-?\d+(?:\.\d+)?)")
    direct_compare = re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]*)|\[['\"]([A-Z][A-Z0-9_]*)['\"]\])\s*(?:===|==|!==|!=)\s*(['\"`][^'\"`]*['\"`]|true|false|-?\d+(?:\.\d+)?)")
    bind = re.compile(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*process\.env(?:\.([A-Z][A-Z0-9_]*)|\[['\"]([A-Z][A-Z0-9_]*)['\"]\])(?P<tail>[^;]*)")
    compare_var = re.compile(r"\b([A-Za-z_$][\w$]*)\s*(?:===|==|!==|!=)\s*(['\"`][^'\"`]*['\"`]|true|false|-?\d+(?:\.\d+)?)")
    default_value = re.compile(r"(?:\?\?|\|\|)\s*(['\"`][^'\"`]*['\"`]|true|false|-?\d+(?:\.\d+)?)")
    feature = re.compile(r"(?:\.isEnabled|\.is_enabled|\.variation|\.getBooleanValue)\(\s*['\"]([A-Za-z0-9_.:-]+)['\"]")

    bindings_by_scope: dict[str, dict[str, str]] = {}
    for lineno, line, scope in _iter_scoped_lines(text, "javascript"):
        detail = f"javascript:{scope}"
        bindings = bindings_by_scope.setdefault(scope, {})

        for pat in (env_read, deno_read, bun_read):
            for match in pat.finditer(line):
                name = next((g for g in match.groups() if g), None)
                if not name:
                    continue
                key = _item(keys, name, language="javascript", category="env")
                loc = Location(rel, lineno, "test" if is_test else "read", detail)
                (key.test_mentions if is_test else key.reads).append(loc)

        for match in bind.finditer(line):
            variable = match.group(1)
            name = match.group(2) or match.group(3)
            bindings[variable] = name
            tail = match.group("tail") or ""
            dm = default_value.search(tail)
            if dm:
                key = _item(keys, name, language="javascript", category="env")
                default = _quoted_value(dm.group(1))
                key.defaults.add(_safe_value(name, default))

        if is_test:
            for match in assignment.finditer(line):
                name = match.group(1) or match.group(2)
                value = _safe_value(name, _quoted_value(match.group(3)))
                key = _item(keys, name, language="javascript", category="env")
                key.test_mentions.append(Location(rel, lineno, "test", detail))
                key.tested_values.add(value)
                key.test_value_observations.setdefault(f"{rel}::{scope}", set()).add(value)

        if not is_test:
            for match in direct_compare.finditer(line):
                name = match.group(1) or match.group(2)
                value = _safe_value(name, _quoted_value(match.group(3)))
                key = _item(keys, name, language="javascript", category="env")
                key.expected_values.add(value)
                key.branch_values.add(value)
                key.branches.append(Location(rel, lineno, "branch", detail))
            for match in compare_var.finditer(line):
                variable, raw = match.groups()
                name = bindings.get(variable)
                if not name:
                    continue
                value = _safe_value(name, _quoted_value(raw))
                key = _item(keys, name, language="javascript", category="env")
                key.expected_values.add(value)
                key.branch_values.add(value)
                key.branches.append(Location(rel, lineno, "branch", detail))

        for match in feature.finditer(line):
            name = match.group(1)
            key = _item(keys, name, language="javascript", category="feature-flag")
            key.expected_values.update({"true", "false"})
            key.branch_values.update({"true", "false"})
            loc = Location(rel, lineno, "test" if is_test else "read", detail)
            (key.test_mentions if is_test else key.reads).append(loc)
            if not is_test:
                key.branches.append(Location(rel, lineno, "branch", detail))


def record_go(text: str, rel: str, is_test: bool, keys: dict[str, ConfigKey]) -> None:
    env_read = re.compile(r"os\.(?:Getenv|LookupEnv)\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)")
    bind = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?::=|=)\s*os\.(?:Getenv|LookupEnv)\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)")
    direct_compare = re.compile(r"os\.(?:Getenv|LookupEnv)\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)\s*(?:==|!=)\s*(['\"][^'\"]*['\"]|true|false|-?\d+(?:\.\d+)?)")
    compare_var = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:==|!=)\s*(['\"][^'\"]*['\"]|true|false|-?\d+(?:\.\d+)?)")
    setenv = re.compile(r"(?:os|t)\.Setenv\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*,\s*(['\"][^'\"]*['\"]|true|false|-?\d+(?:\.\d+)?)\s*\)")

    bindings_by_scope: dict[str, dict[str, str]] = {}
    for lineno, line, scope in _iter_scoped_lines(text, "go"):
        detail = f"go:{scope}"
        bindings = bindings_by_scope.setdefault(scope, {})
        for match in env_read.finditer(line):
            name = match.group(1)
            key = _item(keys, name, language="go", category="env")
            loc = Location(rel, lineno, "test" if is_test else "read", detail)
            (key.test_mentions if is_test else key.reads).append(loc)
        for match in bind.finditer(line):
            bindings[match.group(1)] = match.group(2)

        if is_test:
            for match in setenv.finditer(line):
                name = match.group(1)
                value = _safe_value(name, _quoted_value(match.group(2)))
                key = _item(keys, name, language="go", category="env")
                key.test_mentions.append(Location(rel, lineno, "test", detail))
                key.tested_values.add(value)
                key.test_value_observations.setdefault(f"{rel}::{scope}", set()).add(value)
        else:
            for match in direct_compare.finditer(line):
                name = match.group(1)
                value = _safe_value(name, _quoted_value(match.group(2)))
                key = _item(keys, name, language="go", category="env")
                key.expected_values.add(value)
                key.branch_values.add(value)
                key.branches.append(Location(rel, lineno, "branch", detail))
            for match in compare_var.finditer(line):
                variable, raw = match.groups()
                name = bindings.get(variable)
                if not name:
                    continue
                value = _safe_value(name, _quoted_value(raw))
                key = _item(keys, name, language="go", category="env")
                key.expected_values.add(value)
                key.branch_values.add(value)
                key.branches.append(Location(rel, lineno, "branch", detail))


def record_java_frameworks(text: str, rel: str, is_test: bool, keys: dict[str, ConfigKey]) -> None:
    # Spring @Value("${key:default}")
    value_pat = re.compile(r"@Value\(\s*['\"]\$\{([^}:]+)(?::([^}]*))?\}['\"]\s*\)")
    get_prop = re.compile(r"\b(?:environment|env)\.getProperty\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]*)['\"])?")
    config_props = re.compile(r"@ConfigurationProperties\s*\(\s*(?:prefix\s*=\s*)?['\"]([^'\"]+)['\"]\s*\)")
    field_pat = re.compile(r"^\s*(?:private|protected|public)\s+(boolean|Boolean|String|int|long|double|Integer|Long|Double)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*=\s*([^;]+))?;")
    feature = re.compile(r"\.(?:isEnabled|variation|getBooleanValue)\(\s*['\"]([A-Za-z0-9_.:-]+)['\"]")

    for match in value_pat.finditer(text):
        name, default = match.groups()
        line = text.count("\n", 0, match.start()) + 1
        key = _item(keys, name, language="java", category="spring")
        loc = Location(rel, line, "test" if is_test else "read", "java:spring:@Value")
        (key.test_mentions if is_test else key.reads).append(loc)
        if default is not None and default != "":
            if is_sensitive(name):
                key.sensitive_default_present = True
            key.defaults.add(_safe_value(name, default))

    for match in get_prop.finditer(text):
        name, default = match.groups()
        line = text.count("\n", 0, match.start()) + 1
        key = _item(keys, name, language="java", category="spring")
        loc = Location(rel, line, "test" if is_test else "read", "java:spring:getProperty")
        (key.test_mentions if is_test else key.reads).append(loc)
        if default is not None:
            key.defaults.add(_safe_value(name, default))

    lines = text.splitlines()
    prefix: str | None = None
    depth = 0
    active_depth: int | None = None
    for lineno, line in enumerate(lines, 1):
        m = config_props.search(line)
        if m:
            prefix = m.group(1).rstrip(".")
        opens, closes = _brace_counts(line)
        if prefix and " class " in f" {line} " and opens:
            active_depth = depth + 1
        if prefix and active_depth is not None and depth >= active_depth:
            fm = field_pat.match(line)
            if fm:
                typ, field, default = fm.groups()
                name = f"{prefix}.{field}"
                key = _item(keys, name, language="java", category="spring")
                key.declarations.append(Location(rel, lineno, "declaration", "java:spring:@ConfigurationProperties"))
                if typ in {"boolean", "Boolean"}:
                    key.expected_values.update({"true", "false"})
                if default:
                    clean = default.strip().strip('"\'')
                    key.defaults.add(_safe_value(name, clean))
        depth += opens - closes
        if active_depth is not None and depth < active_depth:
            prefix = None
            active_depth = None

    for match in feature.finditer(text):
        name = match.group(1)
        line = text.count("\n", 0, match.start()) + 1
        key = _item(keys, name, language="java", category="feature-flag")
        key.expected_values.update({"true", "false"})
        key.branch_values.update({"true", "false"})
        loc = Location(rel, line, "test" if is_test else "read", "java:feature-flag")
        (key.test_mentions if is_test else key.reads).append(loc)


def record_dotnet(text: str, rel: str, is_test: bool, keys: dict[str, ConfigKey]) -> None:
    env_pat = re.compile(r"Environment\.GetEnvironmentVariable\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)")
    setenv_pat = re.compile(r"Environment\.SetEnvironmentVariable\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*,\s*(['\"][^'\"]*['\"]|true|false|null|-?\d+(?:\.\d+)?)")
    indexer = re.compile(r"\b(?:configuration|config|builder\.Configuration)\s*\[\s*['\"]([^'\"]+)['\"]\s*\]")
    getvalue = re.compile(r"\.(?:GetValue(?:<[^>]+>)?|GetConnectionString)\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*([^\)]+))?\)")
    feature = re.compile(r"\.IsEnabledAsync?\(\s*['\"]([A-Za-z0-9_.:-]+)['\"]")

    for pattern, category, detail in [
        (env_pat, "env", "dotnet:Environment"),
        (indexer, "settings", "dotnet:IConfiguration"),
    ]:
        for match in pattern.finditer(text):
            name = match.group(1)
            line = text.count("\n", 0, match.start()) + 1
            key = _item(keys, name, language="csharp", category=category)
            loc = Location(rel, line, "test" if is_test else "read", detail)
            (key.test_mentions if is_test else key.reads).append(loc)

    for match in getvalue.finditer(text):
        name, default = match.groups()
        line = text.count("\n", 0, match.start()) + 1
        key = _item(keys, name, language="csharp", category="settings")
        loc = Location(rel, line, "test" if is_test else "read", "dotnet:GetValue")
        (key.test_mentions if is_test else key.reads).append(loc)
        if default:
            key.defaults.add(_safe_value(name, _quoted_value(default.strip())))

    if is_test:
        for match in setenv_pat.finditer(text):
            name, raw = match.groups()
            line = text.count("\n", 0, match.start()) + 1
            key = _item(keys, name, language="csharp", category="env")
            value = _safe_value(name, _quoted_value(raw))
            key.tested_values.add(value)
            key.test_value_observations.setdefault(rel, set()).add(value)
            key.test_mentions.append(Location(rel, line, "test", "dotnet:SetEnvironmentVariable"))

    for match in feature.finditer(text):
        name = match.group(1)
        line = text.count("\n", 0, match.start()) + 1
        key = _item(keys, name, language="csharp", category="feature-flag")
        key.expected_values.update({"true", "false"})
        key.branch_values.update({"true", "false"})
        loc = Location(rel, line, "test" if is_test else "read", "dotnet:feature-flag")
        (key.test_mentions if is_test else key.reads).append(loc)


def record_json_schema(data: object, rel: str, keys: dict[str, ConfigKey]) -> bool:
    """Record JSON Schema-like property domains. Returns True when recognized."""
    if not isinstance(data, dict) or not isinstance(data.get("properties"), dict):
        return False

    def walk(properties: dict[str, object], prefix: str = "") -> None:
        for raw_name, spec in properties.items():
            name = f"{prefix}.{raw_name}" if prefix else str(raw_name)
            if not isinstance(spec, dict):
                continue
            key = _item(keys, name, language="json-schema", category="schema")
            key.declarations.append(Location(rel, 1, "declaration", "json-schema"))
            if "default" in spec:
                default = spec["default"]
                if is_sensitive(name) and str(default):
                    key.sensitive_default_present = True
                key.defaults.add(_safe_value(name, default))
            enum = spec.get("enum")
            if isinstance(enum, list):
                key.expected_values.update(_safe_value(name, x) for x in enum)
                key.validators.add("json-schema:enum")
            if "const" in spec:
                key.expected_values.add(_safe_value(name, spec["const"]))
                key.validators.add("json-schema:const")
            if spec.get("type") == "boolean":
                key.expected_values.update({"true", "false"})
                key.validators.add("json-schema:type=boolean")
            for validator in ("pattern", "minimum", "maximum", "minLength", "maxLength"):
                if validator in spec:
                    key.validators.add(f"json-schema:{validator}={spec[validator]}")
            nested = spec.get("properties")
            if isinstance(nested, dict):
                walk(nested, name)

    walk(data["properties"])
    return True


def record_terraform_domains(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    """Enrich Terraform variables with deterministic finite-domain evidence."""
    for match in re.finditer(r'variable\s+"([A-Za-z_][A-Za-z0-9_-]*)"\s*\{(?P<body>.*?)\n\}', text, re.S):
        name = match.group(1)
        body = match.group("body")
        key = keys.setdefault(name, ConfigKey(name=name))
        key.categories.add("terraform")
        type_match = re.search(r"\btype\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", body)
        if type_match and type_match.group(1) == "bool":
            key.expected_values.update({"true", "false"})
            key.validators.add("terraform:type=bool")
        contains = re.search(r"contains\(\s*\[([^\]]+)\]\s*,\s*var\." + re.escape(name) + r"\s*\)", body, re.S)
        if contains:
            for raw in re.findall(r"['\"]([^'\"]+)['\"]", contains.group(1)):
                key.expected_values.add(_safe_value(name, raw))
            key.validators.add("terraform:contains-domain")
        for raw in re.findall(r"var\." + re.escape(name) + r"\s*(?:==|!=)\s*['\"]([^'\"]+)['\"]", body):
            key.expected_values.add(_safe_value(name, raw))
            key.validators.add("terraform:comparison-domain")
