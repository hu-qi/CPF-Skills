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


orchestrator = load_module(
    "resolve_next_action",
    "scripts/orchestrator/resolve_next_action.py",
)
frameworks, framework_families = orchestrator.load_framework_config(
    ROOT / "resources/frameworks.yaml"
)


def qualification(
    framework: str,
    status: str = "RECOMMENDED",
    *,
    eligible: bool = True,
    pending: list[str] | None = None,
    fixture_only: bool = False,
) -> dict:
    return {
        "fixture_only": fixture_only,
        "framework": framework,
        "candidate": "ExampleLibrary",
        "qualification": {
            "status": status,
            "eligible_to_start_adaptation": eligible,
            "reason": "deterministic test input",
            "pending_checks": pending or [],
        },
        "evidence": [
            "fixture://qualification" if fixture_only else "artifact://qualification"
        ],
    }


def resolve(payload: dict) -> dict:
    return orchestrator.resolve_next_action(
        payload,
        frameworks,
        framework_families,
    )


def test_arkts_recommended_routes_to_official_porting() -> None:
    result = resolve(qualification("applicationtpc-arkts"))
    assert result["fixture_only"] is False
    assert result["framework"] == "arkts"
    assert result["phase"] == "ADAPTATION"
    assert result["decision"] == "PROCEED"
    assert result["route"]["type"] == "OFFICIAL_SKILL"
    assert result["route"]["source"] == "official"
    assert result["route"]["skill"] == "ohos-library-porting"
    assert result["route"]["analysis_skill"] == "ohos-library-migration-analyzer"
    assert result["evidence"] == ["artifact://qualification"]


def test_cpp_recommended_preserves_analysis_but_requires_manual_implementation() -> None:
    result = resolve(qualification("applicationtpc-cpp"))
    assert result["framework"] == "cpp"
    assert result["phase"] == "ADAPTATION"
    assert result["decision"] == "PROCEED"
    assert result["route"]["type"] == "MANUAL_REQUIRED"
    assert result["route"]["source"] == "manual"
    assert result["route"]["skill"] is None
    assert result["route"]["analysis_skill"] == "ohos-library-migration-analyzer"
    assert result["route"]["analysis_source"] == "official"
    assert "ohos-library-migration-analyzer" in result["next_action"]
    assert "不得把分析 Skill 当成完整 porting 实现" in result["next_action"]


def test_flutter_pending_official_check_routes_confirmed_skill() -> None:
    result = resolve(
        qualification(
            "flutter",
            "NEEDS_OFFICIAL_CHECK",
            eligible=False,
            pending=["执行 flutter-library-search 并重新生成 qualification"],
        )
    )
    assert result["phase"] == "QUALIFICATION"
    assert result["decision"] == "BLOCKED"
    assert result["route"]["type"] == "QUALIFICATION_CHECK"
    assert result["route"]["source"] == "official"
    assert result["route"]["skill"] == "flutter-library-search"


def test_excluded_candidate_does_not_route_to_framework_skill() -> None:
    result = resolve(
        qualification(
            "arkts",
            "EXCLUDED_ALREADY_ADAPTED",
            eligible=False,
        )
    )
    assert result["phase"] == "STOPPED"
    assert result["decision"] == "STOP"
    assert result["route"]["skill"] is None
    assert result["route"]["source"] == "manual"


def test_fixture_recommended_case_never_routes_real_official_skill() -> None:
    result = resolve(
        qualification(
            "applicationtpc-arkts",
            fixture_only=True,
        )
    )
    assert result["fixture_only"] is True
    assert result["phase"] == "ADAPTATION"
    assert result["decision"] == "PROCEED"
    assert result["route"]["type"] == "BLOCKED_BY_GATE"
    assert result["route"]["skill"] is None
    assert result["route"]["analysis_skill"] is None
    assert "fixture_only" in result["next_action"]
    assert "不调用官方适配 Skill" in result["next_action"]


def test_fixture_pending_check_never_routes_real_qualification_skill() -> None:
    result = resolve(
        qualification(
            "flutter",
            "NEEDS_OFFICIAL_CHECK",
            eligible=False,
            pending=["执行 flutter-library-search"],
            fixture_only=True,
        )
    )
    assert result["fixture_only"] is True
    assert result["phase"] == "QUALIFICATION"
    assert result["decision"] == "BLOCKED"
    assert result["route"]["skill"] is None
    assert "不调用真实官方 qualification Skill" in result["next_action"]


def test_generic_applicationtpc_cannot_start_adaptation() -> None:
    try:
        resolve(qualification("applicationtpc"))
    except ValueError as exc:
        message = str(exc)
        assert "ambiguous framework family" in message
        assert "arkts" in message
        assert "cpp" in message
    else:
        raise AssertionError("generic ApplicationTPC must not choose a variant implicitly")


def test_multiple_pending_official_skills_are_rejected() -> None:
    try:
        resolve(
            qualification(
                "flutter",
                "NEEDS_OFFICIAL_CHECK",
                eligible=False,
                pending=[
                    "执行 flutter-library-search",
                    "执行 ohos-flutter-plugin-adaptation-necessity-check",
                ],
            )
        )
    except ValueError as exc:
        assert "multiple official Skills" in str(exc)
    else:
        raise AssertionError("multiple pending official skills must be resolved explicitly")


def main() -> None:
    test_arkts_recommended_routes_to_official_porting()
    test_cpp_recommended_preserves_analysis_but_requires_manual_implementation()
    test_flutter_pending_official_check_routes_confirmed_skill()
    test_excluded_candidate_does_not_route_to_framework_skill()
    test_fixture_recommended_case_never_routes_real_official_skill()
    test_fixture_pending_check_never_routes_real_qualification_skill()
    test_generic_applicationtpc_cannot_start_adaptation()
    test_multiple_pending_official_skills_are_rejected()
    print("ORCHESTRATOR NEXT-ACTION TESTS PASSED: real routes compose safely and fixture routes stay non-operational")


if __name__ == "__main__":
    main()
