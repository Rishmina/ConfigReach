from __future__ import annotations

from pathlib import Path

from configreach.models import ConfigKey, Location


class FeatureFlagsFileAdapter:
    """Example config-provider adapter for simple deterministic .featureflags files.

    Format:
        CHECKOUT_V2=false|true
        PAYMENT_MODE=sandbox|live
    """

    name = "feature-flags-file"
    api_version = 1
    parser = "line-oriented-v1"
    deterministic = True
    capabilities = ("config-provider", "finite-domain", "line-provenance")

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".featureflags"

    def scan(self, *, path: Path, rel: str, text: str, is_test: bool, keys: dict[str, ConfigKey]) -> None:
        for line_number, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, raw_values = line.split("=", 1)
            name = name.strip()
            if not name:
                continue
            values = {value.strip() for value in raw_values.split("|") if value.strip()}
            key = keys.setdefault(name, ConfigKey(name=name))
            key.categories.add("feature-flag")
            key.expected_values.update(values)
            key.declarations.append(
                Location(rel, line_number, "declaration", "plugin:feature-flags-file")
            )
