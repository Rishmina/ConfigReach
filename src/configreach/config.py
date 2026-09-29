from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_IGNORES = [
    ".git/**", ".hg/**", ".svn/**", ".venv/**", "venv/**", "node_modules/**",
    "dist/**", "build/**", ".tox/**", ".pytest_cache/**", "__pycache__/**",
    ".configreach/**",
]


@dataclass
class Settings:
    ignores: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORES))
    test_patterns: list[str] = field(default_factory=lambda: [
        "tests/**", "test/**", "**/test_*.py", "**/*_test.py", "**/*.test.js",
        "**/*.test.ts", "**/*.spec.js", "**/*.spec.ts", "**/*_test.go",
    ])
    fail_under: float | None = None

    def ignored(self, rel: str) -> bool:
        rel = rel.replace("\\", "/")
        return any(fnmatch.fnmatch(rel, pattern) for pattern in self.ignores)

    def is_test(self, rel: str) -> bool:
        rel = rel.replace("\\", "/")
        parts = rel.split("/")
        if "tests" in parts or "test" in parts:
            return True
        return any(fnmatch.fnmatch(rel, pattern) for pattern in self.test_patterns)


def load_settings(root: Path) -> Settings:
    settings = Settings()
    path = root / "configreach.toml"
    if not path.exists():
        return settings
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return settings
    section = data.get("configreach", data)
    if isinstance(section.get("ignore"), list):
        settings.ignores.extend(str(x) for x in section["ignore"])
    if isinstance(section.get("test_patterns"), list):
        settings.test_patterns = [str(x) for x in section["test_patterns"]]
    if section.get("fail_under") is not None:
        try:
            settings.fail_under = float(section["fail_under"])
        except (TypeError, ValueError):
            pass
    return settings
