from __future__ import annotations

import json

from configreach.models import ConfigKey, Location, ScanReport
from configreach.planner import build_plan, render_plan


def _key(name: str, values: set[str], tested: set[str], observations: dict[str, set[str]]) -> ConfigKey:
    item = ConfigKey(name=name)
    item.expected_values = set(values)
    item.tested_values = set(tested)
    item.test_value_observations = {scenario: set(vals) for scenario, vals in observations.items()}
    item.reads.append(Location("app.py", 10, "read", "python:handle"))
    return item


def test_pairwise_plan_fills_missing_cross_states() -> None:
    left = _key("MODE", {"sandbox", "live"}, {"sandbox", "live"}, {"t1": {"sandbox"}, "t2": {"live"}})
    right = _key("REGION", {"us", "eu"}, {"us", "eu"}, {"t1": {"us"}, "t2": {"eu"}})
    report = ScanReport(".", {"MODE": left, "REGION": right}, 1, 2)

    plan = build_plan(report, strength=2)
    configs = [case.to_dict()["configuration"] for case in plan.cases]

    assert plan.interactions_total == 4
    assert plan.interactions_already_covered == 2
    assert plan.interactions_remaining == 0
    assert {"MODE": "live", "REGION": "us"} in configs
    assert {"MODE": "sandbox", "REGION": "eu"} in configs


def test_sensitive_keys_are_not_emitted() -> None:
    mode = _key("MODE", {"on", "off"}, {"on"}, {"t1": {"on"}})
    secret = _key("API_TOKEN", {"one", "two"}, set(), {})
    report = ScanReport(".", {"MODE": mode, "API_TOKEN": secret}, 1, 1)

    payload = build_plan(report, strength=1).to_dict()
    assert "API_TOKEN" not in json.dumps(payload)


def test_single_key_gap_is_actionable() -> None:
    item = _key("PAYMENT_MODE", {"sandbox", "live"}, {"sandbox"}, {"test_sandbox": {"sandbox"}})
    item.reads[0] = Location("payment.py", 3, "read", "python:module")
    report = ScanReport(".", {"PAYMENT_MODE": item}, 1, 1)

    plan = build_plan(report, strength=2)
    assert any(case.to_dict()["configuration"] == {"PAYMENT_MODE": "live"} for case in plan.cases)


def test_plan_is_deterministic_and_bounded() -> None:
    a = _key("A", {"0", "1"}, set(), {})
    b = _key("B", {"0", "1"}, set(), {})
    c = _key("C", {"0", "1"}, set(), {})
    report = ScanReport(".", {"A": a, "B": b, "C": c}, 1, 0)

    first = render_plan(build_plan(report, strength=3, max_cases=3), "json")
    second = render_plan(build_plan(report, strength=3, max_cases=3), "json")

    assert first == second
    data = json.loads(first)
    assert len(data["cases"]) == 3
    assert data["warnings"]


def test_markdown_renderer_contains_structured_cases() -> None:
    a = _key("A", {"0", "1"}, {"0"}, {"t": {"0"}})
    b = _key("B", {"x", "y"}, {"x"}, {"t": {"x"}})
    report = ScanReport(".", {"A": a, "B": b}, 1, 1)

    text = render_plan(build_plan(report), "markdown")
    assert "ConfigReach deterministic test plan" in text
    assert "CRP001" in text
    assert "Configuration" in text
