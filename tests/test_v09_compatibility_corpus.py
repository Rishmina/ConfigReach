from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from configreach.engine import scan


ROOT = Path(__file__).resolve().parents[1]


def test_offline_polyglot_compatibility_corpus() -> None:
    corpus = json.loads((ROOT / "compatibility" / "corpus.json").read_text(encoding="utf-8"))
    assert corpus["schema_version"] == 1
    for fixture in corpus["fixtures"]:
        report = scan(ROOT / fixture["path"], use_cache=False)
        expected = set(fixture["required_keys"])
        assert expected <= set(report.keys), (fixture["name"], sorted(expected - set(report.keys)))
        assert report.to_dict()["schema_version"] == 5


def test_feature_flag_provider_example_is_executable(tmp_path: Path) -> None:
    module_path = ROOT / "examples" / "plugins" / "feature_flags_provider" / "configreach_feature_flags.py"
    spec = importlib.util.spec_from_file_location("configreach_feature_flags_example", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    adapter = module.FeatureFlagsFileAdapter()
    keys = {}
    adapter.scan(
        path=tmp_path / "sample.featureflags",
        rel="sample.featureflags",
        text="CHECKOUT_V2=false|true\nPAYMENT_MODE=sandbox|live\n",
        is_test=False,
        keys=keys,
    )
    assert keys["CHECKOUT_V2"].expected_values == {"false", "true"}
    assert keys["PAYMENT_MODE"].expected_values == {"sandbox", "live"}
    assert "feature-flag" in keys["CHECKOUT_V2"].categories


def test_optional_parser_examples_compile_without_importing_dependencies() -> None:
    examples = [
        ROOT / "examples" / "plugins" / "tree_sitter_js" / "configreach_tree_sitter_js.py",
        ROOT / "examples" / "plugins" / "tree_sitter_go" / "configreach_tree_sitter_go.py",
    ]
    for path in examples:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
