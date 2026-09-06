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


gate = load_module(
    "resolve_qualification_gate",
    "scripts/orchestrator/resolve_qualification_gate.py",
)


def fixture(
    status: str,
    *,
    eligible: bool,
    pending: list[str] | None = None,
) -> dict:
    return {
        "framework": "flutter",
        "candidate": "ExamplePlugin",
        "qualification": {
            "status": status,
            "eligible_to_start_adaptation": eligible,
            "reason": "fixture",
            "pending_checks": pending or [],
        },
    }


def test_recommended_proceeds() -> None:
    result = gate.resolve_gate(fixture("RECOMMENDED", eligible=True))
    assert result["phase"] == "ADAPTATION"
    assert result["decision"] == "PROCEED"


def test_recommended_contract_conflict_blocks() -> None:
    result = gate.resolve_gate(fixture("RECOMMENDED", eligible=False))
    assert result["phase"] == "QUALIFICATION"
    assert result["decision"] == "BLOCKED"

    result = gate.resolve_gate(
        fixture("RECOMMENDED", eligible=True, pending=["still blocking"])
    )
    assert result["phase"] == "QUALIFICATION"
    assert result["decision"] == "BLOCKED"


def test_needs_official_check_blocks() -> None:
    result = gate.resolve_gate(
        fixture(
            "NEEDS_OFFICIAL_CHECK",
            eligible=False,
            pending=["执行 flutter-library-search"],
        )
    )
    assert result["phase"] == "QUALIFICATION"
    assert result["decision"] == "BLOCKED"
    assert result["pending_checks"] == ["执行 flutter-library-search"]


def test_exclusions_stop() -> None:
    for status in (
        "EXCLUDED_ALREADY_ADAPTED",
        "EXCLUDED_NO_ADAPTATION_NEEDED",
        "EXCLUDED_LOW_VALUE",
        "EXCLUDED_UNVERIFIABLE",
    ):
        result = gate.resolve_gate(fixture(status, eligible=False))
        assert result["phase"] == "STOPPED"
        assert result["decision"] == "STOP"
        assert result["qualification_status"] == status


def test_invalid_artifact_is_rejected() -> None:
    bad = fixture("RECOMMENDED", eligible=True)
    bad["qualification"]["status"] = "ADAPTED"
    try:
        gate.resolve_gate(bad)
    except ValueError as exc:
        assert "unsupported qualification.status" in str(exc)
    else:
        raise AssertionError("invalid status must be rejected")


def main() -> None:
    test_recommended_proceeds()
    test_recommended_contract_conflict_blocks()
    test_needs_official_check_blocks()
    test_exclusions_stop()
    test_invalid_artifact_is_rejected()
    print("ORCHESTRATOR GATE TESTS PASSED: deterministic qualification gating is stable")


if __name__ == "__main__":
    main()
