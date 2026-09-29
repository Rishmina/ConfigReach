from __future__ import annotations

import ast
import configparser
import json
import re
import tomllib
from pathlib import Path
from typing import Iterable

from .config import Settings, load_settings
from .models import ConfigKey, Location, ScanReport, is_sensitive


TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs", ".rb", ".php",
    ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
    ".conf", ".properties", ".tf", ".env", ".example", ".template", ".mk",
}
TEXT_NAMES = {"Dockerfile", "Makefile", "Procfile", "action.yml", "action.yaml"}
MAX_FILE_SIZE = 2_000_000

GENERIC_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("javascript", re.compile(r"process\.env(?:\.([A-Z][A-Z0-9_]+)|\[['\"]([A-Z][A-Z0-9_]+)['\"]\])"), "env"),
    ("go", re.compile(r"os\.(?:Getenv|LookupEnv)\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)"), "env"),
    ("java", re.compile(r"System\.(?:getenv|getProperty)\(\s*['\"]([A-Za-z_][A-Za-z0-9_.-]*)['\"]\s*\)"), "env"),
    ("rust", re.compile(r"(?:std::)?env::var\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)"), "env"),
    ("ruby", re.compile(r"ENV(?:\[['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\]|\.fetch\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\))"), "env"),
    ("php", re.compile(r"getenv\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\)"), "env"),
]

TEST_VALUE_PATTERNS = [
    re.compile(r"(?:setenv|set_env|setEnv)\(\s*['\"](?P<key>[A-Za-z_][A-Za-z0-9_.-]*)['\"]\s*,\s*['\"](?P<value>[^'\"]*)['\"]"),
    re.compile(r"(?:os\.environ|process\.env)(?:\[['\"](?P<key>[A-Za-z_][A-Za-z0-9_]*)['\"]\]|\.(?P<key2>[A-Z][A-Z0-9_]+))\s*=\s*['\"](?P<value>[^'\"]*)['\"]"),
]


def _safe_value(name: str, value: object) -> str:
    if value is None:
        return "<none>"
    if is_sensitive(name):
        return "<set>"
    text = str(value)
    return text if len(text) <= 120 else text[:117] + "..."


def _literal(node: ast.AST | None) -> object | None:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


class PythonVisitor(ast.NodeVisitor):
    def __init__(self, rel: str, is_test: bool, keys: dict[str, ConfigKey]):
        self.rel = rel
        self.is_test = is_test
        self.keys = keys

    def item(self, name: str) -> ConfigKey:
        key = self.keys.setdefault(name, ConfigKey(name=name))
        key.languages.add("python")
        return key

    def _record_read(self, name: str, node: ast.AST, default: object | None = None) -> None:
        key = self.item(name)
        key.categories.add("env")
        loc = Location(self.rel, getattr(node, "lineno", 1), "test" if self.is_test else "read", "python")
        if self.is_test:
            key.test_mentions.append(loc)
        else:
            key.reads.append(loc)
        if default is not None:
            key.defaults.add(_safe_value(name, default))

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute):
            dotted = self._dotted(func)
            if dotted in {"os.getenv", "os.environ.get"} and node.args:
                name = _literal(node.args[0])
                if isinstance(name, str):
                    default = _literal(node.args[1]) if len(node.args) > 1 else None
                    self._record_read(name, node, default)
            elif func.attr == "add_argument" and node.args:
                flag = _literal(node.args[0])
                if isinstance(flag, str) and flag.startswith("--"):
                    name = flag[2:].replace("-", "_").upper()
                    key = self.item(name)
                    key.categories.add("cli")
                    loc = Location(self.rel, getattr(node, "lineno", 1), "test" if self.is_test else "declaration", flag)
                    (key.test_mentions if self.is_test else key.declarations).append(loc)
                    for kw in node.keywords:
                        if kw.arg == "default":
                            val = _literal(kw.value)
                            if val is not None:
                                key.defaults.add(_safe_value(name, val))
                        if kw.arg == "choices":
                            vals = _literal(kw.value)
                            if isinstance(vals, (list, tuple, set)):
                                key.expected_values.update(_safe_value(name, x) for x in vals)
            elif dotted.endswith("monkeypatch.setenv") and len(node.args) >= 2:
                name, value = _literal(node.args[0]), _literal(node.args[1])
                if isinstance(name, str):
                    key = self.item(name)
                    key.categories.add("env")
                    key.test_mentions.append(Location(self.rel, getattr(node, "lineno", 1), "test", "monkeypatch.setenv"))
                    if value is not None:
                        key.tested_values.add(_safe_value(name, value))
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._dotted(node.value) == "os.environ":
            name = _literal(node.slice)
            if isinstance(name, str):
                self._record_read(name, node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        name = self._env_name_from_expr(node.left)
        if name and node.comparators:
            value = _literal(node.comparators[0])
            if value is not None:
                self.item(name).expected_values.add(_safe_value(name, value))
        self.generic_visit(node)

    def _env_name_from_expr(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if self._dotted(node.func) in {"os.getenv", "os.environ.get"} and node.args:
                value = _literal(node.args[0])
                return value if isinstance(value, str) else None
        if isinstance(node, ast.Subscript) and self._dotted(node.value) == "os.environ":
            value = _literal(node.slice)
            return value if isinstance(value, str) else None
        return None

    @staticmethod
    def _dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            left = PythonVisitor._dotted(node.value)
            return f"{left}.{node.attr}" if left else node.attr
        return ""


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _record_generic(text: str, rel: str, is_test: bool, keys: dict[str, ConfigKey]) -> None:
    for language, pattern, category in GENERIC_PATTERNS:
        for match in pattern.finditer(text):
            name = next((g for g in match.groups() if g), None)
            if not name:
                continue
            key = keys.setdefault(name, ConfigKey(name=name))
            key.languages.add(language)
            key.categories.add(category)
            loc = Location(rel, _line_number(text, match.start()), "test" if is_test else "read", language)
            (key.test_mentions if is_test else key.reads).append(loc)

    if is_test:
        for pattern in TEST_VALUE_PATTERNS:
            for match in pattern.finditer(text):
                gd = match.groupdict()
                name = gd.get("key") or gd.get("key2")
                value = gd.get("value")
                if not name:
                    continue
                key = keys.setdefault(name, ConfigKey(name=name))
                key.test_mentions.append(Location(rel, _line_number(text, match.start()), "test", "assignment"))
                if value is not None:
                    key.tested_values.add(_safe_value(name, value))


def _record_env_file(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not match:
            continue
        name, value = match.groups()
        key = keys.setdefault(name, ConfigKey(name=name))
        key.categories.add("env")
        key.declarations.append(Location(rel, lineno, "declaration", "env-file"))
        if value:
            key.defaults.add(_safe_value(name, value.strip('"\'')))


def _flatten(prefix: str, obj: object) -> Iterable[tuple[str, object]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten(dotted, value)
    elif isinstance(obj, list):
        yield prefix, f"<list:{len(obj)}>"
    elif prefix:
        yield prefix, obj


def _record_structured(path: Path, text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    suffix = path.suffix.lower()
    data: object | None = None
    try:
        if suffix == ".json":
            data = json.loads(text)
        elif suffix == ".toml":
            data = tomllib.loads(text)
        elif suffix in {".ini", ".cfg"}:
            parser = configparser.ConfigParser()
            parser.read_string(text)
            data = {section: dict(parser[section]) for section in parser.sections()}
    except Exception:
        data = None
    if data is not None:
        for name, value in _flatten("", data):
            key = keys.setdefault(name, ConfigKey(name=name))
            key.categories.add("settings")
            key.declarations.append(Location(rel, 1, "declaration", suffix.lstrip(".")))
            if not isinstance(value, (dict, list)):
                key.defaults.add(_safe_value(name, value))


def _record_yaml(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        match = re.match(r"^\s{0,12}([A-Z][A-Z0-9_]{2,})\s*:\s*(.*?)\s*$", line)
        if match:
            name, value = match.groups()
            key = keys.setdefault(name, ConfigKey(name=name))
            key.categories.add("deployment")
            key.declarations.append(Location(rel, idx, "declaration", "yaml"))
            if value and value not in {"|", ">", "{}", "[]"}:
                key.defaults.add(_safe_value(name, value.strip('"\'')))
        name_match = re.match(r"^\s*-?\s*name:\s*([A-Z][A-Z0-9_]{2,})\s*$", line)
        if name_match and idx < len(lines):
            name = name_match.group(1)
            key = keys.setdefault(name, ConfigKey(name=name))
            key.categories.add("deployment")
            key.declarations.append(Location(rel, idx, "declaration", "yaml-env"))


def _record_terraform(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    for match in re.finditer(r'variable\s+"([A-Za-z_][A-Za-z0-9_-]*)"\s*\{', text):
        name = match.group(1)
        key = keys.setdefault(name, ConfigKey(name=name))
        key.categories.add("terraform")
        key.declarations.append(Location(rel, _line_number(text, match.start()), "declaration", "terraform"))


def _record_makefile(text: str, rel: str, keys: dict[str, ConfigKey]) -> None:
    for lineno, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^([A-Z][A-Z0-9_]{2,})\s*(?:\?=|:=|=)\s*(.*)$", line)
        if match:
            name, value = match.groups()
            key = keys.setdefault(name, ConfigKey(name=name))
            key.categories.add("make")
            key.declarations.append(Location(rel, lineno, "declaration", "make"))
            if value:
                key.defaults.add(_safe_value(name, value))


def _eligible(path: Path) -> bool:
    if path.name.startswith(".env"):
        return True
    if path.name in TEXT_NAMES:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def scan(root: str | Path = ".", settings: Settings | None = None) -> ScanReport:
    root_path = Path(root).resolve()
    settings = settings or load_settings(root_path)
    keys: dict[str, ConfigKey] = {}
    files_scanned = 0
    tests_scanned = 0
    warnings: list[str] = []

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root_path).as_posix()
        if settings.ignored(rel) or not _eligible(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                warnings.append(f"Skipped large file: {rel}")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(f"Could not read {rel}: {exc}")
            continue

        files_scanned += 1
        is_test = settings.is_test(rel)
        tests_scanned += int(is_test)

        if path.suffix.lower() == ".py":
            try:
                tree = ast.parse(text, filename=rel)
                PythonVisitor(rel, is_test, keys).visit(tree)
            except SyntaxError:
                warnings.append(f"Python parse failed: {rel}")

        _record_generic(text, rel, is_test, keys)
        lower_name = path.name.lower()
        if lower_name.startswith(".env") or lower_name.endswith((".example", ".template")):
            _record_env_file(text, rel, keys)
        if path.suffix.lower() in {".json", ".toml", ".ini", ".cfg"} and path.name != "configreach.toml":
            _record_structured(path, text, rel, keys)
        if path.suffix.lower() in {".yaml", ".yml"}:
            _record_yaml(text, rel, keys)
        if path.suffix.lower() == ".tf":
            _record_terraform(text, rel, keys)
        if path.name == "Makefile" or path.suffix.lower() == ".mk":
            _record_makefile(text, rel, keys)

    test_files: list[tuple[str, str]] = []
    for path in root_path.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root_path).as_posix()
            if settings.is_test(rel) and not settings.ignored(rel) and _eligible(path):
                try:
                    test_files.append((rel, path.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    pass
    for name, key in keys.items():
        if key.test_mentions:
            continue
        token = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
        for rel, text in test_files:
            match = token.search(text)
            if match:
                key.test_mentions.append(Location(rel, _line_number(text, match.start()), "test", "name-reference"))
                break

    return ScanReport(str(root_path), keys, files_scanned, tests_scanned, warnings)
