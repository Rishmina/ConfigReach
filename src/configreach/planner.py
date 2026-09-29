from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations, product
from typing import Any

from .models import ScanReport, is_sensitive


@dataclass(frozen=True)
class PlanCase:
    case_id: str
    scope: str
    assignments: tuple[tuple[str, str], ...]
    covers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.case_id,
            "scope": self.scope,
            "configuration": {key: value for key, value in self.assignments},
            "covers": list(self.covers),
        }


@dataclass
class TestPlan:
    strength: int
    cases: list[PlanCase]
    missing_values: dict[str, list[str]]
    interactions_total: int
    interactions_already_covered: int
    interactions_planned: int
    interactions_remaining: int
    scopes_considered: int
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "strength": self.strength,
            "summary": {
                "cases": len(self.cases),
                "scopes_considered": self.scopes_considered,
                "interactions_total": self.interactions_total,
                "interactions_already_covered": self.interactions_already_covered,
                "interactions_planned": self.interactions_planned,
                "interactions_remaining": self.interactions_remaining,
                "missing_value_inputs": len(self.missing_values),
            },
            "missing_values": self.missing_values,
            "cases": [case.to_dict() for case in self.cases],
            "warnings": self.warnings,
        }


def _interaction_token(interaction: tuple[tuple[str, str], ...]) -> str:
    return " & ".join(f"{key}={value}" for key, value in interaction)


def _observed_interactions(
    keys: dict[str, Any], names: list[str], strength: int
) -> set[tuple[tuple[str, str], ...]]:
    scenarios: set[str] = set()
    for name in names:
        scenarios.update(keys[name].test_value_observations)
    observed: set[tuple[tuple[str, str], ...]] = set()
    for scenario in sorted(scenarios):
        for subset in combinations(names, strength):
            value_sets = [sorted(keys[name].test_value_observations.get(scenario, set())) for name in subset]
            if not all(value_sets):
                continue
            for values in product(*value_sets):
                observed.add(tuple(zip(subset, values)))
    return observed


def build_plan(
    report: ScanReport,
    *,
    strength: int = 2,
    max_cases: int = 64,
    max_domain: int = 12,
    max_interactions: int = 20000,
) -> TestPlan:
    """Build a deterministic bounded covering-array style plan from known finite domains.

    The planner never executes target code and never invents values. It only uses finite values
    already discovered by ConfigReach plus explicit test-value observations.
    """
    if strength not in {1, 2, 3}:
        raise ValueError("strength must be 1, 2, or 3")
    if max_cases < 1:
        raise ValueError("max_cases must be at least 1")
    if max_domain < 1:
        raise ValueError("max_domain must be at least 1")
    if max_interactions < 1:
        raise ValueError("max_interactions must be at least 1")

    warnings: list[str] = []
    missing_values: dict[str, list[str]] = {}
    for item in sorted(report.effective_keys, key=lambda x: x.name):
        if is_sensitive(item.name) or not item.expected_values:
            continue
        missing = sorted(item.expected_values - item.tested_values)
        if missing:
            missing_values[item.name] = missing

    planned: list[tuple[str, tuple[tuple[str, str], ...], tuple[str, ...]]] = []
    total_required = 0
    total_already = 0
    total_planned_interactions = 0
    total_remaining = 0
    scopes_considered = 0
    case_limit_reached = False

    for scope, scope_names in sorted(report.dependency_scopes.items()):
        names = [
            name
            for name in sorted(scope_names)
            if name in report.keys
            and not report.keys[name].baseline_ignored
            and not is_sensitive(name)
            and report.keys[name].expected_values
        ]
        if len(names) < strength:
            continue
        oversized = [name for name in names if len(report.keys[name].expected_values) > max_domain]
        if oversized:
            warnings.append(
                f"Skipped {scope}: finite domain exceeds max_domain={max_domain} for {', '.join(oversized)}"
            )
            continue

        scopes_considered += 1
        required: set[tuple[tuple[str, str], ...]] = set()
        overflow = False
        for subset in combinations(names, strength):
            domains = [sorted(report.keys[name].expected_values) for name in subset]
            for values in product(*domains):
                required.add(tuple(zip(subset, values)))
                if len(required) > max_interactions:
                    overflow = True
                    break
            if overflow:
                break
        if overflow:
            warnings.append(
                f"Skipped {scope}: required interactions exceed max_interactions={max_interactions}"
            )
            continue

        observed = _observed_interactions(report.keys, names, strength)
        already = required & observed
        uncovered = set(required - already)
        total_required += len(required)
        total_already += len(already)
        if not uncovered:
            continue

        defaults = {name: sorted(report.keys[name].expected_values)[0] for name in names}
        candidates: set[tuple[tuple[str, str], ...]] = set()
        for interaction in sorted(uncovered):
            assignment = dict(defaults)
            assignment.update(interaction)
            candidates.add(tuple((name, assignment[name]) for name in names))

        while uncovered and candidates and len(planned) < max_cases:
            scored: list[
                tuple[
                    int,
                    tuple[tuple[str, str], ...],
                    set[tuple[tuple[str, str], ...]],
                ]
            ] = []
            for candidate in candidates:
                mapping = dict(candidate)
                covered = {
                    interaction
                    for interaction in uncovered
                    if all(mapping.get(key) == value for key, value in interaction)
                }
                scored.append((len(covered), candidate, covered))
            best_score = max(score for score, _, _ in scored)
            if best_score <= 0:
                break
            best = min(
                (entry for entry in scored if entry[0] == best_score),
                key=lambda entry: entry[1],
            )
            _, candidate, covered = best
            planned.append(
                (
                    scope,
                    candidate,
                    tuple(sorted(_interaction_token(item) for item in covered)),
                )
            )
            total_planned_interactions += len(covered)
            uncovered.difference_update(covered)
            candidates.discard(candidate)

        total_remaining += len(uncovered)
        if uncovered:
            warnings.append(
                f"Plan truncated for {scope}: {len(uncovered)} interactions remain uncovered"
            )
        if len(planned) >= max_cases:
            case_limit_reached = True
            break

    if case_limit_reached:
        warnings.append(
            "Plan case limit reached; later dependency scopes may not have been evaluated"
        )

    # Single-key finite-domain gaps remain actionable even when a key does not participate
    # in an N-wise dependency scope. Avoid duplicating values already present in planned cases.
    planned_values = {
        (key, value)
        for _, assignment, _ in planned
        for key, value in assignment
    }
    for name, values in sorted(missing_values.items()):
        for value in values:
            if (name, value) in planned_values:
                continue
            if len(planned) >= max_cases:
                if "Plan truncated before all single-key value gaps could be suggested" not in warnings:
                    warnings.append(
                        "Plan truncated before all single-key value gaps could be suggested"
                    )
                break
            planned.append(("<single-key>", ((name, value),), (f"{name}={value}",)))
            planned_values.add((name, value))
        if len(planned) >= max_cases:
            break

    cases = [
        PlanCase(f"CRP{index:03d}", scope, assignment, covers)
        for index, (scope, assignment, covers) in enumerate(planned, 1)
    ]
    return TestPlan(
        strength=strength,
        cases=cases,
        missing_values=missing_values,
        interactions_total=total_required,
        interactions_already_covered=total_already,
        interactions_planned=total_planned_interactions,
        interactions_remaining=total_remaining,
        scopes_considered=scopes_considered,
        warnings=warnings,
    )


def render_plan(plan: TestPlan, format_name: str = "text") -> str:
    if format_name == "json":
        return json.dumps(plan.to_dict(), indent=2, sort_keys=True) + "\n"

    if format_name == "markdown":
        data = plan.to_dict()["summary"]
        lines = [
            "# ConfigReach deterministic test plan",
            "",
            f"- Strength: **{plan.strength}-wise**",
            f"- Suggested cases: **{data['cases']}**",
            f"- Interactions already covered: **{data['interactions_already_covered']} / {data['interactions_total']}**",
            f"- Interactions remaining after plan: **{data['interactions_remaining']}**",
            "",
        ]
        if plan.cases:
            lines += [
                "| Case | Scope | Configuration | Covers |",
                "|---|---|---|---:|",
            ]
            for case in plan.cases:
                config = "<br>".join(f"`{key}={value}`" for key, value in case.assignments)
                lines.append(
                    f"| `{case.case_id}` | `{case.scope}` | {config} | {len(case.covers)} |"
                )
        else:
            lines.append(
                "No additional deterministic cases are suggested from the known finite domains."
            )
        if plan.warnings:
            lines += ["", "## Warnings"] + [f"- {warning}" for warning in plan.warnings]
        return "\n".join(lines) + "\n"

    if format_name != "text":
        raise ValueError(f"unsupported plan format: {format_name}")

    lines = [
        "ConfigReach deterministic test plan",
        f"Strength: {plan.strength}-wise",
        f"Suggested cases: {len(plan.cases)}",
        f"Interactions: {plan.interactions_already_covered}/{plan.interactions_total} already covered; "
        f"{plan.interactions_remaining} remain after plan",
        "",
    ]
    for case in plan.cases:
        assignments = ", ".join(f"{key}={value}" for key, value in case.assignments)
        lines.append(
            f"{case.case_id} [{case.scope}] {assignments}  (covers {len(case.covers)} gaps)"
        )
    if not plan.cases:
        lines.append(
            "No additional deterministic cases are suggested from the known finite domains."
        )
    if plan.warnings:
        lines += ["", "Warnings:"] + [f"- {warning}" for warning in plan.warnings]
    return "\n".join(lines) + "\n"
