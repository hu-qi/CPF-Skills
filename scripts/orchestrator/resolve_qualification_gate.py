from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {
    "RECOMMENDED",
    "NEEDS_OFFICIAL_CHECK",
    "EXCLUDED_ALREADY_ADAPTED",
    "EXCLUDED_NO_ADAPTATION_NEEDED",
    "EXCLUDED_LOW_VALUE",
    "EXCLUDED_UNVERIFIABLE",
}

EXCLUDED_STATUSES = {
    "EXCLUDED_ALREADY_ADAPTED",
    "EXCLUDED_NO_ADAPTATION_NEEDED",
    "EXCLUDED_LOW_VALUE",
    "EXCLUDED_UNVERIFIABLE",
}


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def resolve_gate(payload: dict[str, Any]) -> dict[str, Any]:
    framework = payload.get("framework")
    candidate = payload.get("candidate")
    if not isinstance(framework, str) or not framework.strip():
        raise ValueError("framework must be a non-empty string")
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("candidate must be a non-empty string")

    qualification = require_dict(payload.get("qualification"), "qualification")
    status = qualification.get("status")
    eligible = qualification.get("eligible_to_start_adaptation")
    pending_checks = qualification.get("pending_checks", [])
    reason = qualification.get("reason")

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported qualification.status: {status!r}")
    if not isinstance(eligible, bool):
        raise ValueError("qualification.eligible_to_start_adaptation must be boolean")
    if not isinstance(pending_checks, list) or not all(
        isinstance(item, str) for item in pending_checks
    ):
        raise ValueError("qualification.pending_checks must be a string list")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("qualification.reason must be a string when present")

    result: dict[str, Any] = {
        "schema_version": 1,
        "framework": framework,
        "candidate": candidate,
        "qualification_status": status,
        "phase": None,
        "decision": None,
        "next_action": None,
        "pending_checks": list(pending_checks),
        "reason": reason or "",
    }

    if status in EXCLUDED_STATUSES:
        result.update(
            {
                "phase": "STOPPED",
                "decision": "STOP",
                "next_action": "不要开始该候选的重复适配；保留排除证据并选择其他候选。",
            }
        )
        return result

    if status == "NEEDS_OFFICIAL_CHECK":
        result.update(
            {
                "phase": "QUALIFICATION",
                "decision": "BLOCKED",
                "next_action": "完成 pending_checks 中的官方检查或 required 去重，并重新生成 qualification。",
            }
        )
        return result

    # RECOMMENDED must be internally consistent before adaptation is allowed.
    if not eligible:
        result.update(
            {
                "phase": "QUALIFICATION",
                "decision": "BLOCKED",
                "next_action": "qualification 契约冲突：RECOMMENDED 但 eligible_to_start_adaptation != true；重新生成 qualification。",
            }
        )
        return result

    if pending_checks:
        result.update(
            {
                "phase": "QUALIFICATION",
                "decision": "BLOCKED",
                "next_action": "RECOMMENDED 仍含未完成 pending_checks；完成后重新生成 qualification。",
            }
        )
        return result

    result.update(
        {
            "phase": "ADAPTATION",
            "decision": "PROCEED",
            "next_action": "按当前框架官方 Skills 路由进入实际适配；不得把资格检查 Skill 当作适配实现 Skill。",
        }
    )
    return result


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: resolve_qualification_gate.py <qualification-json> <gate-json>"
        )

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("qualification artifact must be a JSON object")

    try:
        gate = resolve_gate(payload)
    except ValueError as exc:
        raise SystemExit(f"invalid qualification artifact: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Orchestrator gate: {gate['candidate']} -> "
        f"{gate['phase']}/{gate['decision']}"
    )


if __name__ == "__main__":
    main()
