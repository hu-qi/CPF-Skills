from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative: str) -> ModuleType:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


route = load_module(
    "resolve_framework_route",
    "scripts/orchestrator/resolve_framework_route.py",
)
frameworks, framework_families = route.load_framework_config(ROOT / "resources/frameworks.yaml")


def gate_fixture(framework: str, *, fixture_only: bool = False) -> dict:
    return {
        "fixture_only": fixture_only,
        "framework": framework,
        "candidate": "ExampleLibrary",
        "phase": "ADAPTATION",
        "decision": "PROCEED",
    }


def resolve(framework: str) -> dict:
    return route.resolve_route(
        gate_fixture(framework),
        frameworks,
        framework_families,
    )


def test_applicationtpc_arkts_routes_to_official_porting() -> None:
    for framework in ("arkts", "applicationtpc-arkts"):
        result = resolve(framework)
        assert result["fixture_only"] is False
        assert result["framework"] == "arkts"
        assert result["route_type"] == "OFFICIAL_SKILL"
        assert result["route_skill"] == "ohos-library-porting"
        assert result["analysis_skill"] == "ohos-library-migration-analyzer"
        assert result["official_repository"] == "https://atomgit.com/CPF-ApplicationTPC/skills"


def test_applicationtpc_cpp_routes_to_analysis_then_manual_implementation() -> None:
    for framework in ("cpp", "c++", "c-cpp", "applicationtpc-cpp"):
        result = resolve(framework)
        assert result["framework"] == "cpp"
        assert result["route_type"] == "MANUAL_REQUIRED"
        assert result["route_skill"] is None
        assert result["analysis_skill"] == "ohos-library-migration-analyzer"
        assert result["official_repository"] == "https://atomgit.com/CPF-ApplicationTPC/skills"


def test_generic_applicationtpc_requires_explicit_variant() -> None:
    for framework in ("applicationtpc", "ApplicationTPC", "application-tpc"):
        try:
            resolve(framework)
        except ValueError as exc:
            message = str(exc)
            assert "ambiguous framework family" in message
            assert "arkts" in message
            assert "cpp" in message
        else:
            raise AssertionError("ApplicationTPC family name must require an explicit variant")


def test_blocked_gate_cannot_reach_official_porting() -> None:
    blocked = gate_fixture("arkts")
    blocked["phase"] = "QUALIFICATION"
    blocked["decision"] = "BLOCKED"

    result = route.resolve_route(blocked, frameworks, framework_families)
    assert result["framework"] == "arkts"
    assert result["route_type"] == "BLOCKED_BY_GATE"
    assert result["route_skill"] is None
    assert result["analysis_skill"] is None


def test_fixture_gate_is_non_operational_even_when_state_is_proceed() -> None:
    fixture_gate = gate_fixture("arkts", fixture_only=True)
    result = route.resolve_route(fixture_gate, frameworks, framework_families)
    assert result["fixture_only"] is True
    assert result["gate_phase"] == "ADAPTATION"
    assert result["gate_decision"] == "PROCEED"
    assert result["route_type"] == "BLOCKED_BY_GATE"
    assert result["route_skill"] is None
    assert result["analysis_skill"] is None
    assert "fixture_only" in result["reason"]


def test_duplicate_framework_alias_is_rejected() -> None:
    duplicated = {
        "first": {"aliases": ["shared"]},
        "second": {"aliases": ["shared"]},
    }
    try:
        route.resolve_framework_key("shared", duplicated, {})
    except ValueError as exc:
        assert "ambiguous framework alias" in str(exc)
    else:
        raise AssertionError("duplicate aliases must not resolve by configuration order")


def main() -> None:
    test_applicationtpc_arkts_routes_to_official_porting()
    test_applicationtpc_cpp_routes_to_analysis_then_manual_implementation()
    test_generic_applicationtpc_requires_explicit_variant()
    test_blocked_gate_cannot_reach_official_porting()
    test_fixture_gate_is_non_operational_even_when_state_is_proceed()
    test_duplicate_framework_alias_is_rejected()
    print("FRAMEWORK ROUTE TESTS PASSED: real routes are explicit and fixture routes are non-operational")


if __name__ == "__main__":
    main()
