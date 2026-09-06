from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_CHECKS = (
    "implementation",
    "build",
    "demo",
    "tests",
    "device_run",
    "screenshots",
)

ALLOWED_CHECK_STATUSES = {
    "VERIFIED",
    "FAILED",
    "NOT_RUN",
    "MISSING",
}

PHYSICAL_DEVICE_PLATFORMS = {"HarmonyOS", "OpenHarmony"}


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    return list(value)


def validate_check(name: str, raw: Any) -> dict[str, Any]:
    check = require_dict(raw, f"validation.checks.{name}")
    status = check.get("status")
    if status not in ALLOWED_CHECK_STATUSES:
        raise ValueError(
            f"validation.checks.{name}.status must be one of "
            + ", ".join(sorted(ALLOWED_CHECK_STATUSES))
        )

    evidence = require_string_list(
        check.get("evidence", []),
        f"validation.checks.{name}.evidence",
    )

    if status == "VERIFIED" and not evidence:
        raise ValueError(
            f"validation.checks.{name} is VERIFIED but has no evidence references"
        )

    normalized: dict[str, Any] = {
        "status": status,
        "evidence": evidence,
    }

    if name == "device_run":
        details = require_dict(check.get("details", {}), "validation.checks.device_run.details")
        device_kind = details.get("device_kind")
        platform = details.get("platform")
        if status == "VERIFIED":
            if device_kind != "physical":
                raise ValueError(
                    "validation.checks.device_run VERIFIED requires details.device_kind=physical"
                )
            if platform not in PHYSICAL_DEVICE_PLATFORMS:
                raise ValueError(
                    "validation.checks.device_run VERIFIED requires details.platform "
                    "to be HarmonyOS or OpenHarmony"
                )
        normalized["details"] = {
            "device_kind": device_kind,
            "platform": platform,
            "device_model": details.get("device_model"),
        }

    return normalized


def resolve_validation_gate(payload: dict[str, Any]) -> dict[str, Any]:
    framework = payload.get("framework")
    candidate = payload.get("candidate")
    if not isinstance(framework, str) or not framework.strip():
        raise ValueError("framework must be a non-empty string")
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("candidate must be a non-empty string")

    validation = require_dict(payload.get("validation"), "validation")
    checks = require_dict(validation.get("checks"), "validation.checks")

    normalized_checks: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_CHECKS:
        if name not in checks:
            raise ValueError(f"validation.checks.{name} is required")
        normalized_checks[name] = validate_check(name, checks[name])

    unknown = sorted(set(checks) - set(REQUIRED_CHECKS))
    if unknown:
        raise ValueError("unsupported validation checks: " + ", ".join(unknown))

    failed = [
        name
        for name, check in normalized_checks.items()
        if check["status"] == "FAILED"
    ]
    incomplete = [
        name
        for name, check in normalized_checks.items()
        if check["status"] in {"NOT_RUN", "MISSING"}
    ]

    evidence: list[str] = []
    for name in REQUIRED_CHECKS:
        for ref in normalized_checks[name]["evidence"]:
            if ref not in evidence:
                evidence.append(ref)

    if failed or incomplete:
        pending_checks = [
            *(f"修复并重新验证 {name}" for name in failed),
            *(f"补齐并验证 {name}" for name in incomplete),
        ]
        reason_parts: list[str] = []
        if failed:
            reason_parts.append("failed=" + ",".join(failed))
        if incomplete:
            reason_parts.append("incomplete=" + ",".join(incomplete))
        return {
            "schema_version": 1,
            "framework": framework,
            "candidate": candidate,
            "phase": "VALIDATION",
            "decision": "BLOCKED",
            "next_action": "完成所有真实适配、构建、Demo、测试、真机运行与截图证据后重新执行 validation gate。",
            "pending_checks": pending_checks,
            "checks": normalized_checks,
            "evidence": evidence,
            "reason": "; ".join(reason_parts),
        }

    return {
        "schema_version": 1,
        "framework": framework,
        "candidate": candidate,
        "phase": "ARTICLE_PREP",
        "decision": "PROCEED",
        "next_action": "整理 qualification、代码变更、构建/测试日志、真机运行与截图等真实素材，进入文章准备阶段。",
        "pending_checks": [],
        "checks": normalized_checks,
        "evidence": evidence,
        "reason": "all required validation checks are VERIFIED with evidence",
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: resolve_validation_gate.py <validation-json> <validation-gate-json>"
        )

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("validation artifact must be a JSON object")

    try:
        result = resolve_validation_gate(payload)
    except ValueError as exc:
        raise SystemExit(f"invalid validation artifact: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Validation gate: {result['candidate']} -> "
        f"{result['phase']}/{result['decision']}"
    )


if __name__ == "__main__":
    main()
