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


builder = load_module(
    "build_article_material_pack",
    "scripts/article/build_article_material_pack.py",
)


def qualification(status: str = "RECOMMENDED", *, fixture_only: bool = False) -> dict:
    return {
        "fixture_only": fixture_only,
        "framework": "arkts",
        "candidate": "ExampleLibrary",
        "qualification": {
            "status": status,
            "eligible_to_start_adaptation": status == "RECOMMENDED",
            "pending_checks": [],
        },
        "evidence": ["fixture://qualification" if fixture_only else "artifact://qualification"],
    }


def validation(ready: bool = True, *, fixture_only: bool = False) -> dict:
    checks = {}
    prefix = "fixture://" if fixture_only else "artifact://"
    for name in builder.REQUIRED_VALIDATION_CHECKS:
        checks[name] = {
            "status": "VERIFIED" if ready else "MISSING",
            "evidence": [f"{prefix}{name}"] if ready else [],
        }
    return {
        "fixture_only": fixture_only,
        "framework": "arkts",
        "candidate": "ExampleLibrary",
        "phase": "ARTICLE_PREP" if ready else "VALIDATION",
        "decision": "PROCEED" if ready else "BLOCKED",
        "checks": checks,
    }


def notes(*, complete: bool = True, fixture_only: bool = False) -> dict:
    prefix = "fixture://" if fixture_only else "artifact://"
    return {
        "fixture_only": fixture_only,
        "summary": "真实适配记录摘要" if not fixture_only else "合成测试记录摘要",
        "problems": [{"title": "真实问题", "evidence": [f"{prefix}problem"]}] if complete else [],
        "decisions": [{"decision": "真实取舍", "evidence": [f"{prefix}decision"]}] if complete else [],
        "api_changes": [{"api": "foo", "change": "平台实现补齐"}] if complete else [],
        "source_refs": [f"{prefix}abc", f"{prefix}build"] if complete else [],
    }


def test_ready_inputs_build_grounded_material_pack() -> None:
    pack = builder.build_material_pack(qualification(), validation(), notes())
    assert pack["framework"] == "arkts"
    assert pack["candidate"] == "ExampleLibrary"
    assert pack["fixture_only"] is False
    assert pack["qualification_status"] == "RECOMMENDED"
    assert pack["validation_status"] == "ARTICLE_PREP/PROCEED"
    assert len(pack["section_plan"]) == 6
    assert pack["material_gaps"] == []
    assert pack["ai_boundary"]["full_article_generation_allowed"] is False
    assert "主体实践叙述" in pack["ai_boundary"]["author_required"]


def test_incomplete_development_notes_create_gaps_not_fiction() -> None:
    pack = builder.build_material_pack(qualification(), validation(), notes(complete=False))
    assert len(pack["material_gaps"]) == 4
    assert any("不能虚构" in item for item in pack["material_gaps"])
    problems_section = next(item for item in pack["section_plan"] if item["section"] == "问题、尝试与解决过程")
    assert any("只写真实发生" in prompt for prompt in problems_section["author_prompts"])


def test_non_recommended_candidate_cannot_build_article_pack() -> None:
    try:
        builder.build_material_pack(
            qualification("EXCLUDED_ALREADY_ADAPTED"),
            validation(),
            notes(),
        )
    except ValueError as exc:
        assert "qualification.status=RECOMMENDED" in str(exc)
    else:
        raise AssertionError("non-recommended candidate must not enter article material preparation")


def test_validation_must_be_article_prep_proceed() -> None:
    try:
        builder.build_material_pack(qualification(), validation(ready=False), notes())
    except ValueError as exc:
        assert "ARTICLE_PREP/PROCEED" in str(exc)
    else:
        raise AssertionError("blocked validation must not build article material pack")


def test_candidate_and_framework_must_match() -> None:
    bad_validation = validation()
    bad_validation["candidate"] = "OtherLibrary"
    try:
        builder.build_material_pack(qualification(), bad_validation, notes())
    except ValueError as exc:
        assert "candidate mismatch" in str(exc)
    else:
        raise AssertionError("candidate mismatch must be rejected")


def test_fixture_mode_must_match_across_inputs() -> None:
    pack = builder.build_material_pack(
        qualification(fixture_only=True),
        validation(fixture_only=True),
        notes(fixture_only=True),
    )
    assert pack["fixture_only"] is True

    try:
        builder.build_material_pack(
            qualification(fixture_only=True),
            validation(fixture_only=True),
            notes(fixture_only=False),
        )
    except ValueError as exc:
        assert "fixture_only flags must match" in str(exc)
    else:
        raise AssertionError("fixture mode mismatch must be rejected")


def main() -> None:
    test_ready_inputs_build_grounded_material_pack()
    test_incomplete_development_notes_create_gaps_not_fiction()
    test_non_recommended_candidate_cannot_build_article_pack()
    test_validation_must_be_article_prep_proceed()
    test_candidate_and_framework_must_match()
    test_fixture_mode_must_match_across_inputs()
    print("ARTICLE MATERIAL PACK TESTS PASSED: writing inputs stay evidence-grounded")


if __name__ == "__main__":
    main()
