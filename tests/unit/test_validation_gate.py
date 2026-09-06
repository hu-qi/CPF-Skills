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


validation_gate = load_module(
    "resolve_validation_gate",
    "scripts/orchestrator/resolve_validation_gate.py",
)


def verified_check(name: str, *, prefix: str = "artifact://") -> dict:
    check = {
        "status": "VERIFIED",
        "evidence": [f"{prefix}{name}"],
    }
    if name == "device_run":
        check["details"] = {
            "device_kind": "physical",
            "platform": "HarmonyOS",
            "device_model": "fixture-device",
        }
    return check


def artifact() -> dict:
    return {
        "framework": "arkts",
        "candidate": "ExampleLibrary",
        "validation": {
            "checks": {
                name: verified_check(name)
                for name in validation_gate.REQUIRED_CHECKS
            }
        },
    }


def test_all_verified_enters_article_prep() -> None:
    result = validation_gate.resolve_validation_gate(artifact())
    assert result["phase"] == "ARTICLE_PREP"
    assert result["decision"] == "PROCEED"
    assert result["pending_checks"] == []
    assert result["fixture_only"] is False
    assert len(result["evidence"]) == len(validation_gate.REQUIRED_CHECKS)


def test_failed_and_missing_checks_block() -> None:
    payload = artifact()
    payload["validation"]["checks"]["build"] = {
        "status": "FAILED",
        "evidence": ["log://build-failure"],
    }
    payload["validation"]["checks"]["screenshots"] = {
        "status": "MISSING",
        "evidence": [],
    }
    result = validation_gate.resolve_validation_gate(payload)
    assert result["phase"] == "VALIDATION"
    assert result["decision"] == "BLOCKED"
    assert "修复并重新验证 build" in result["pending_checks"]
    assert "补齐并验证 screenshots" in result["pending_checks"]


def test_verified_requires_evidence() -> None:
    payload = artifact()
    payload["validation"]["checks"]["tests"] = {
        "status": "VERIFIED",
        "evidence": [],
    }
    try:
        validation_gate.resolve_validation_gate(payload)
    except ValueError as exc:
        assert "VERIFIED but has no evidence" in str(exc)
    else:
        raise AssertionError("VERIFIED without evidence must be rejected")


def test_device_run_must_be_physical_harmony_device() -> None:
    payload = artifact()
    payload["validation"]["checks"]["device_run"]["details"]["device_kind"] = "emulator"
    try:
        validation_gate.resolve_validation_gate(payload)
    except ValueError as exc:
        assert "device_kind=physical" in str(exc)
    else:
        raise AssertionError("emulator must not satisfy device-run evidence")

    payload = artifact()
    payload["validation"]["checks"]["device_run"]["details"]["platform"] = "Android"
    try:
        validation_gate.resolve_validation_gate(payload)
    except ValueError as exc:
        assert "HarmonyOS or OpenHarmony" in str(exc)
    else:
        raise AssertionError("non-Harmony platform must not satisfy device-run evidence")


def test_missing_required_check_is_rejected() -> None:
    payload = artifact()
    del payload["validation"]["checks"]["demo"]
    try:
        validation_gate.resolve_validation_gate(payload)
    except ValueError as exc:
        assert "validation.checks.demo is required" in str(exc)
    else:
        raise AssertionError("missing required check must be rejected")


def test_unknown_check_is_rejected() -> None:
    payload = artifact()
    payload["validation"]["checks"]["marketing"] = {
        "status": "VERIFIED",
        "evidence": ["artifact://marketing"],
    }
    try:
        validation_gate.resolve_validation_gate(payload)
    except ValueError as exc:
        assert "unsupported validation checks" in str(exc)
    else:
        raise AssertionError("unknown checks must be rejected")


def test_fixture_evidence_requires_explicit_fixture_mode() -> None:
    payload = artifact()
    for name in validation_gate.REQUIRED_CHECKS:
        payload["validation"]["checks"][name] = verified_check(name, prefix="fixture://")
    try:
        validation_gate.resolve_validation_gate(payload)
    except ValueError as exc:
        assert "fixture:// evidence is test-only" in str(exc)
    else:
        raise AssertionError("fixture evidence must not enter a normal validation artifact")

    payload["fixture_only"] = True
    result = validation_gate.resolve_validation_gate(payload)
    assert result["fixture_only"] is True
    assert result["phase"] == "ARTICLE_PREP"


def main() -> None:
    test_all_verified_enters_article_prep()
    test_failed_and_missing_checks_block()
    test_verified_requires_evidence()
    test_device_run_must_be_physical_harmony_device()
    test_missing_required_check_is_rejected()
    test_unknown_check_is_rejected()
    test_fixture_evidence_requires_explicit_fixture_mode()
    print("VALIDATION GATE TESTS PASSED: article prep requires complete physical-device evidence")


if __name__ == "__main__":
    main()
