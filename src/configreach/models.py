from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


SENSITIVE_MARKERS = (
    "SECRET", "TOKEN", "PASSWORD", "PASSWD", "API_KEY", "PRIVATE_KEY", "CREDENTIAL",
)


def is_sensitive(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in SENSITIVE_MARKERS)


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
    languages: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)

    @property
    def covered(self) -> bool:
        return bool(self.test_mentions or self.tested_values)

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

    def public_value(self, value: str) -> str:
        return "<redacted>" if is_sensitive(self.name) else value

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "covered": self.covered,
            "declared": self.declared,
            "used": self.used,
            "sensitive": is_sensitive(self.name),
            "reads": [asdict(x) for x in sorted(set(self.reads))],
            "declarations": [asdict(x) for x in sorted(set(self.declarations))],
            "test_mentions": [asdict(x) for x in sorted(set(self.test_mentions))],
            "defaults": sorted(self.public_value(x) for x in self.defaults),
            "expected_values": sorted(self.public_value(x) for x in self.expected_values),
            "tested_values": sorted(self.public_value(x) for x in self.tested_values),
            "languages": sorted(self.languages),
            "categories": sorted(self.categories),
            "value_coverage": self.value_coverage,
        }


@dataclass
class ScanReport:
    root: str
    keys: dict[str, ConfigKey]
    files_scanned: int
    tests_scanned: int
    warnings: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.keys)

    @property
    def covered(self) -> int:
        return sum(1 for item in self.keys.values() if item.covered)

    @property
    def uncovered(self) -> int:
        return self.total - self.covered

    @property
    def coverage(self) -> float:
        return 1.0 if self.total == 0 else self.covered / self.total

    @property
    def undeclared_used(self) -> int:
        return sum(1 for item in self.keys.values() if item.used and not item.declared)

    @property
    def declared_unused(self) -> int:
        return sum(1 for item in self.keys.values() if item.declared and not item.used)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "root": self.root,
            "summary": {
                "files_scanned": self.files_scanned,
                "tests_scanned": self.tests_scanned,
                "configuration_inputs": self.total,
                "covered_inputs": self.covered,
                "uncovered_inputs": self.uncovered,
                "coverage": round(self.coverage, 6),
                "undeclared_used": self.undeclared_used,
                "declared_unused": self.declared_unused,
            },
            "keys": [self.keys[name].to_dict() for name in sorted(self.keys)],
            "warnings": self.warnings,
        }

    def key(self, name: str) -> ConfigKey | None:
        return self.keys.get(name)

    def keys_for_paths(self, paths: set[str]) -> list[ConfigKey]:
        out: list[ConfigKey] = []
        for item in self.keys.values():
            locations = item.reads + item.declarations
            if any(loc.path in paths for loc in locations):
                out.append(item)
        return sorted(out, key=lambda x: x.name)
