from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Protocol

from .models import ConfigKey


class Adapter(Protocol):
    """Public plugin protocol for third-party configuration adapters."""

    name: str

    def supports(self, path: Path) -> bool: ...

    def scan(self, *, path: Path, rel: str, text: str, is_test: bool, keys: dict[str, ConfigKey]) -> None: ...


@dataclass
class LoadedAdapter:
    name: str
    adapter: Adapter


def load_adapters() -> tuple[list[LoadedAdapter], list[str]]:
    loaded: list[LoadedAdapter] = []
    warnings: list[str] = []
    try:
        eps = entry_points(group="configreach.adapters")
    except TypeError:  # pragma: no cover - compatibility with older importlib metadata APIs
        eps = entry_points().get("configreach.adapters", [])
    for ep in eps:
        try:
            obj = ep.load()
            adapter = obj() if isinstance(obj, type) else obj
            if not hasattr(adapter, "supports") or not hasattr(adapter, "scan"):
                raise TypeError("adapter must implement supports() and scan()")
            loaded.append(LoadedAdapter(ep.name, adapter))
        except Exception as exc:  # plugin failures must never crash core scanning
            warnings.append(f"Plugin {ep.name!r} could not be loaded: {exc}")
    return loaded, warnings
