from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any


SENSITIVE_MARKERS = (
    "SECRET", "TOKEN", "PASSWORD", "PASSWD", "API_KEY", "PRIVATE_KEY", "CREDENTIAL",
    "ACCESS_KEY", "CLIENT_SECRET", "CONNECTION_STRING",
)


def is_sensitive(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in SENSITIVE_MARKERS)


def normalized_name(name: str) -> str:
    return "".join(ch for ch in name.upper() if ch.isalnum())


@dataclass(frozen=True, order=True)
class Location:
    path: str
    line: int = 1
    kind: str = "read"
    detail: str = ""


@dataclass
class ConfigKey:
    name: str
    reads: list[Location] = field(default_factory=list)
    declarations: list[Location] = field(default_factory=list)
    test_mentions: list[Location] = field(default_factory=list)
    defaults: set[str] = field(default_factory=set)
    expected_values: set[str] = field(default_factory=set)
    tested_values: set[str] = field(default_factory=set)
    branch_values: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    validators: set[str] = field(default_factory=set)
    runtime_observed: bool = False
    baseline_ignored: bool = False
    sensitive_default_present: bool = False

    @property
    def covered(self) -> bool:
        return bool(self.test_mentions or self.tested_values or self.runtime_observed)

    @property
    def declared(self) -> bool:
        return bool(self.declarations)

    @property
    def used(self) -> bool:
        return bool(self.reads)

    @property
    def value_coverage(self) -> float | None:
        if not self.expected_values:
            return None
        return len(self.expected_values & self.tested_values) / len(self.expected_values)

    @property
    def branch_coverage(self) -> float | None:
        if not self.branch_values:
            return None
        return len(self.branch_values & self.tested_values) / len(self.branch_values)

    @property
    def blast_radius_files(self) -> int:
        return len({loc.path for loc in self.reads})

    @property
    def blast_radius_modules(self) -> int:
        modules = set()
        for loc in self.reads:
            parts = loc.path.split("/")
            modules.add(parts[0] if len(parts) > 1 else ".")
        return len(modules)

    @property
    def modules(self) -> set[str]:
        out: set[str] = set()
        for loc in self.reads + self.declarations + self.test_mentions:
            parts = loc.path.split("/")
            out.add(parts[0] if len(parts) > 1 else ".")
        return out

    @property
    def functions(self) -> set[str]:
        out: set[str] = set()
        for loc in self.reads:
            if loc.detail.startswith("python:"):
                value = loc.detail.split(":", 1)[1]
                if value and value != "module":
                    out.add(value)
        return out

    @property
    def unsafe_sensitive_default(self) -> bool:
        if not is_sensitive(self.name):
            return False
        return self.sensitive_default_present

    def public_value(self, value: str) -> str:
        return "<redacted>" if is_sensitive(self.name) else value

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "covered": self.covered,
            "declared": self.declared,
            "used": self.used,
            "sensitive": is_sensitive(self.name),
            "baseline_ignored": self.baseline_ignored,
            "runtime_observed": self.runtime_observed,
            "reads": [asdict(x) for x in sorted(set(self.reads))],
            "declarations": [asdict(x) for x in sorted(set(self.declarations))],
            "test_mentions": [asdict(x) for x in sorted(set(self.test_mentions))],
            "defaults": sorted(self.public_value(x) for x in self.defaults),
            "expected_values": sorted(self.public_value(x) for x in self.expected_values),
            "tested_values": sorted(self.public_value(x) for x in self.tested_values),
            "branch_values": sorted(self.public_value(x) for x in self.branch_values),
            "languages": sorted(self.languages),
            "categories": sorted(self.categories),
            "validators": sorted(self.validators),
            "value_coverage": self.value_coverage,
            "branch_coverage": self.branch_coverage,
            "blast_radius_files": self.blast_radius_files,
            "blast_radius_modules": self.blast_radius_modules,
            "modules": sorted(self.modules),
            "functions": sorted(self.functions),
            "unsafe_sensitive_default": self.unsafe_sensitive_default,
            "sensitive_default_present": self.sensitive_default_present,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigKey":
        item = cls(name=str(data["name"]))
        item.reads = [Location(**x) for x in data.get("reads", [])]
        item.declarations = [Location(**x) for x in data.get("declarations", [])]
        item.test_mentions = [Location(**x) for x in data.get("test_mentions", [])]
        item.defaults = set(data.get("defaults", []))
        item.expected_values = set(data.get("expected_values", []))
        item.tested_values = set(data.get("tested_values", []))
        item.branch_values = set(data.get("branch_values", []))
        item.languages = set(data.get("languages", []))
        item.categories = set(data.get("categories", []))
        item.validators = set(data.get("validators", []))
        item.runtime_observed = bool(data.get("runtime_observed", False))
        item.baseline_ignored = bool(data.get("baseline_ignored", False))
        item.sensitive_default_present = bool(data.get("sensitive_default_present", False))
        return item


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    message: str
    key: str
    location: Location | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.location is not None:
            data["location"] = asdict(self.location)
        return data


@dataclass
class ScanReport:
    root: str
    keys: dict[str, ConfigKey]
    files_scanned: int
    tests_scanned: int
    warnings: list[str] = field(default_factory=list)
    scan_seconds: float = 0.0
    cache_hit: bool = False
    package_roots: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.keys)

    @property
    def effective_keys(self) -> list[ConfigKey]:
        return [item for item in self.keys.values() if not item.baseline_ignored]

    @property
    def effective_total(self) -> int:
        return len(self.effective_keys)

    @property
    def covered(self) -> int:
        return sum(1 for item in self.effective_keys if item.covered)

    @property
    def uncovered(self) -> int:
        return self.effective_total - self.covered

    @property
    def coverage(self) -> float:
        return 1.0 if self.effective_total == 0 else self.covered / self.effective_total

    @property
    def baseline_ignored(self) -> int:
        return sum(1 for item in self.keys.values() if item.baseline_ignored)

    @property
    def undeclared_used(self) -> int:
        return sum(1 for item in self.effective_keys if item.used and not item.declared)

    @property
    def declared_unused(self) -> int:
        return sum(1 for item in self.effective_keys if item.declared and not item.used)

    @property
    def known_value_inputs(self) -> int:
        return sum(1 for item in self.effective_keys if item.expected_values)

    @property
    def value_coverage(self) -> float | None:
        expected = sum(len(item.expected_values) for item in self.effective_keys)
        if expected == 0:
            return None
        hit = sum(len(item.expected_values & item.tested_values) for item in self.effective_keys)
        return hit / expected

    @property
    def branch_coverage(self) -> float | None:
        expected = sum(len(item.branch_values) for item in self.effective_keys)
        if expected == 0:
            return None
        hit = sum(len(item.branch_values & item.tested_values) for item in self.effective_keys)
        return hit / expected

    @property
    def enum_coverage(self) -> float | None:
        boolset = {"true", "false"}
        items = [item for item in self.effective_keys if item.expected_values and {x.lower() for x in item.expected_values} != boolset]
        expected = sum(len(item.expected_values) for item in items)
        if expected == 0:
            return None
        hit = sum(len(item.expected_values & item.tested_values) for item in items)
        return hit / expected

    @property
    def boolean_inputs(self) -> int:
        boolset = {"true", "false"}
        return sum(1 for item in self.effective_keys if {x.lower() for x in item.expected_values} >= boolset)

    @property
    def boolean_coverage(self) -> float | None:
        boolset = {"true", "false"}
        bool_items = [item for item in self.effective_keys if {x.lower() for x in item.expected_values} >= boolset]
        if not bool_items:
            return None
        total, hit = 0, 0
        for item in bool_items:
            expected = {x for x in item.expected_values if x.lower() in boolset}
            tested_lower = {x.lower() for x in item.tested_values}
            total += len(expected)
            hit += sum(1 for x in expected if x.lower() in tested_lower)
        return hit / total if total else None

    @property
    def pairwise_pairs(self) -> set[tuple[str, str]]:
        by_source: dict[str, set[str]] = {}
        for item in self.effective_keys:
            for loc in item.reads:
                by_source.setdefault(loc.path, set()).add(item.name)
        pairs: set[tuple[str, str]] = set()
        for names in by_source.values():
            for a, b in combinations(sorted(names), 2):
                pairs.add((a, b))
        return pairs

    @property
    def covered_pairs(self) -> set[tuple[str, str]]:
        tests_by_key = {
            name: {loc.path for loc in item.test_mentions}
            for name, item in self.keys.items()
            if not item.baseline_ignored
        }
        out = set()
        for a, b in self.pairwise_pairs:
            if tests_by_key.get(a, set()) & tests_by_key.get(b, set()):
                out.add((a, b))
        return out

    @property
    def combination_coverage(self) -> float | None:
        total = len(self.pairwise_pairs)
        return None if total == 0 else len(self.covered_pairs) / total

    @property
    def findings(self) -> list[Finding]:
        out: list[Finding] = []
        groups: dict[str, list[str]] = {}
        for item in self.keys.values():
            groups.setdefault(normalized_name(item.name), []).append(item.name)
        alias_groups = {k: v for k, v in groups.items() if len(set(v)) > 1}

        for item in sorted(self.effective_keys, key=lambda x: x.name):
            locs = item.reads or item.declarations or item.test_mentions
            loc = locs[0] if locs else None
            if not item.covered:
                out.append(Finding("CR001", "warning", f"{item.name} is not exercised by the detected test suite", item.name, loc))
            if item.used and not item.declared:
                out.append(Finding("CR002", "warning", f"{item.name} is read by application code but no declaration was detected", item.name, loc))
            if item.declared and not item.used:
                out.append(Finding("CR003", "note", f"{item.name} is declared but no application read was detected", item.name, loc))
            if item.expected_values and item.value_coverage is not None and item.value_coverage < 1:
                missing = sorted(item.expected_values - item.tested_values)
                out.append(Finding("CR004", "warning", f"{item.name} has untested values: {', '.join(missing)}", item.name, loc))
            if item.unsafe_sensitive_default:
                out.append(Finding("CR005", "error", f"{item.name} looks sensitive and has a non-empty default", item.name, loc))
            missing_values = item.expected_values - item.tested_values
            risky = sorted(v for v in missing_values if v.lower() in {"prod", "production", "live", "real"})
            if risky:
                out.append(Finding("CR007", "warning", f"{item.name} has production-like untested values: {', '.join(risky)}", item.name, loc))
            aliases = alias_groups.get(normalized_name(item.name))
            if aliases:
                out.append(Finding("CR006", "warning", f"Potential inconsistent configuration naming: {', '.join(sorted(set(aliases)))}", item.name, loc))
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "root": self.root,
            "summary": {
                "files_scanned": self.files_scanned,
                "tests_scanned": self.tests_scanned,
                "configuration_inputs": self.total,
                "effective_inputs": self.effective_total,
                "baseline_ignored": self.baseline_ignored,
                "covered_inputs": self.covered,
                "uncovered_inputs": self.uncovered,
                "coverage": round(self.coverage, 6),
                "value_coverage": None if self.value_coverage is None else round(self.value_coverage, 6),
                "branch_coverage": None if self.branch_coverage is None else round(self.branch_coverage, 6),
                "enum_coverage": None if self.enum_coverage is None else round(self.enum_coverage, 6),
                "boolean_coverage": None if self.boolean_coverage is None else round(self.boolean_coverage, 6),
                "pairwise_combinations": len(self.pairwise_pairs),
                "covered_pairwise_combinations": len(self.covered_pairs),
                "combination_coverage": None if self.combination_coverage is None else round(self.combination_coverage, 6),
                "undeclared_used": self.undeclared_used,
                "declared_unused": self.declared_unused,
                "findings": len(self.findings),
                "package_roots": self.package_roots,
            },
            "keys": [self.keys[name].to_dict() for name in sorted(self.keys)],
            "findings": [f.to_dict() for f in self.findings],
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanReport":
        summary = data.get("summary", {})
        keys = {item["name"]: ConfigKey.from_dict(item) for item in data.get("keys", [])}
        return cls(
            root=str(data.get("root", ".")),
            keys=keys,
            files_scanned=int(summary.get("files_scanned", 0)),
            tests_scanned=int(summary.get("tests_scanned", 0)),
            warnings=list(data.get("warnings", [])),
            scan_seconds=float(summary.get("scan_seconds", 0.0)),
            cache_hit=bool(summary.get("cache_hit", False)),
            package_roots=list(summary.get("package_roots", [])),
        )

    def key(self, name: str) -> ConfigKey | None:
        return self.keys.get(name)

    def keys_for_paths(self, paths: set[str]) -> list[ConfigKey]:
        out: list[ConfigKey] = []
        for item in self.keys.values():
            locations = item.reads + item.declarations
            if any(loc.path in paths for loc in locations):
                out.append(item)
        return sorted(out, key=lambda x: x.name)
