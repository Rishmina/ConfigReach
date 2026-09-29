from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol

from .models import ConfigKey

ADAPTER_API_VERSION = 1


class Adapter(Protocol):
    """Public plugin protocol for third-party configuration adapters."""

    name: str

    def supports(self, path: Path) -> bool: ...

    def scan(self, *, path: Path, rel: str, text: str, is_test: bool, keys: dict[str, ConfigKey]) -> None: ...


@dataclass
class LoadedAdapter:
    name: str
    adapter: Adapter
    api_version: int = ADAPTER_API_VERSION
    parser: str = "unspecified"
    deterministic: bool = True
    capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "api_version": self.api_version,
            "parser": self.parser,
            "deterministic": self.deterministic,
            "capabilities": list(self.capabilities),
        }


def _entry_points():
    try:
        return entry_points(group="configreach.adapters")
    except TypeError:  # pragma: no cover - compatibility with older importlib metadata APIs
        return entry_points().get("configreach.adapters", [])


def _normalize_capabilities(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(sorted({str(item) for item in value}))  # type: ignore[arg-type]
    except TypeError:
        return (str(value),)


def _load_one(ep) -> LoadedAdapter:
    obj = ep.load()
    adapter = obj() if isinstance(obj, type) else obj
    if not hasattr(adapter, "supports") or not callable(adapter.supports):
        raise TypeError("adapter must implement callable supports(path)")
    if not hasattr(adapter, "scan") or not callable(adapter.scan):
        raise TypeError("adapter must implement callable scan(...)")

    api_version = int(getattr(adapter, "api_version", ADAPTER_API_VERSION))
    if api_version != ADAPTER_API_VERSION:
        raise TypeError(
            f"unsupported adapter api_version={api_version}; core supports {ADAPTER_API_VERSION}"
        )
    deterministic = bool(getattr(adapter, "deterministic", True))
    if not deterministic:
        raise TypeError("adapter must declare deterministic=True")

    return LoadedAdapter(
        name=str(getattr(adapter, "name", ep.name)),
        adapter=adapter,
        api_version=api_version,
        parser=str(getattr(adapter, "parser", "unspecified")),
        deterministic=deterministic,
        capabilities=_normalize_capabilities(getattr(adapter, "capabilities", ())),
    )


def load_adapters() -> tuple[list[LoadedAdapter], list[str]]:
    loaded: list[LoadedAdapter] = []
    warnings: list[str] = []
    for ep in _entry_points():
        try:
            loaded.append(_load_one(ep))
        except Exception as exc:  # plugin failures must never crash core scanning
            warnings.append(f"Plugin {ep.name!r} could not be loaded: {exc}")
    loaded.sort(key=lambda item: item.name)
    return loaded, warnings


def adapter_inventory() -> dict[str, Any]:
    loaded, warnings = load_adapters()
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "plugins": [item.to_dict() for item in loaded],
        "warnings": warnings,
    }
