from __future__ import annotations

from pathlib import Path

import pytest

from configreach.capabilities import BUILTIN_CAPABILITIES, builtin_capability_document
from configreach.engine import scan
from configreach.plugins import ADAPTER_API_VERSION, _load_one
from configreach.reproducibility import report_digest, verify_reproducibility


class _EntryPoint:
    name = "demo"

    def __init__(self, obj):
        self.obj = obj

    def load(self):
        return self.obj


class _GoodAdapter:
    name = "demo-parser"
    api_version = ADAPTER_API_VERSION
    parser = "tree-sitter-demo"
    deterministic = True
    capabilities = ("env-read", "function-scope")

    def supports(self, path: Path) -> bool:
        return path.suffix == ".demo"

    def scan(self, *, path, rel, text, is_test, keys) -> None:
        return None


def test_builtin_capability_registry_is_versioned() -> None:
    data = builtin_capability_document()
    assert data["schema_version"] == 1
    assert len(data["builtins"]) == len(BUILTIN_CAPABILITIES)
    assert any(item["adapter_id"] == "python-ast" for item in data["builtins"])


def test_plugin_contract_metadata() -> None:
    loaded = _load_one(_EntryPoint(_GoodAdapter))
    assert loaded.name == "demo-parser"
    assert loaded.api_version == ADAPTER_API_VERSION
    assert loaded.parser == "tree-sitter-demo"
    assert loaded.capabilities == ("env-read", "function-scope")


def test_incompatible_plugin_is_rejected() -> None:
    class BadVersion(_GoodAdapter):
        api_version = 999

    with pytest.raises(TypeError, match="unsupported adapter api_version"):
        _load_one(_EntryPoint(BadVersion))


def test_nondeterministic_plugin_is_rejected() -> None:
    class RandomAdapter(_GoodAdapter):
        deterministic = False

    with pytest.raises(TypeError, match="deterministic=True"):
        _load_one(_EntryPoint(RandomAdapter))


def test_reproducibility_digest_is_stable(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        'import os\nMODE = os.getenv("MODE", "sandbox")\n', encoding="utf-8"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text(
        'def test_mode(monkeypatch):\n    monkeypatch.setenv("MODE", "sandbox")\n',
        encoding="utf-8",
    )
    one = scan(tmp_path, use_cache=False)
    two = scan(tmp_path, use_cache=False)
    assert report_digest(one) == report_digest(two)

    result = verify_reproducibility(scan, str(tmp_path), runs=3)
    assert result.reproducible is True
    assert len({item.digest for item in result.runs}) == 1


def test_reproducibility_run_bounds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 2 and 10"):
        verify_reproducibility(scan, str(tmp_path), runs=1)
