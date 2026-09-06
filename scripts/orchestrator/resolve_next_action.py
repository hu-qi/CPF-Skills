from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from resolve_framework_route import (  # noqa: E402
    load_framework_config,
    resolve_framework_key,
    resolve_route,
)
from resolve_qualification_gate import resolve_gate  # noqa: E402


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def configured_official_skill_names(skills: dict[str, Any]) -> list[str]:
    ignored_keys = {"repository", "audit_status", "audit_commit"}
    names: list[str] = []
    for key, value in skills.items():
        if key in ignored_keys or not isinstance(value, str):
            continue
        if value.startswith("http://") or value.startswith("https://"):
            continue
        names.append(value)
    return sorted(set(names))


def find_pending_official_skill(
    pending_checks: list[str],
    skills: dict[str, Any],
) -> str | None:
    known = configured_official_skill_names(skills)
    matches = {
        skill
        for check in pending_checks
        for skill in known
        if skill in check
    }
    if len(matches) > 1:
        raise ValueError(
            "pending_checks reference multiple official Skills; split or complete them before routing: "
            + ", ".join(sorted(matches))
        )
    return next(iter(matches), None)


def manual_route() -> dict[str, Any]:
    return {
        "skill": None,
        "source": "manual",
        "type": None,
        "analysis_skill": None,
        "analysis_source": None,
        "official_repository": None,
    }


def resolve_next_action(
    payload: dict[str, Any],
    frameworks: dict[str, Any],
    framework_families: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = resolve_gate(payload)
    result: dict[str, Any] = {
        "schema_version": 1,
        "framework": gate["framework"],
        "candidate": gate["candidate"],
        "phase": gate["phase"],
        "decision": gate["decision"],
        "qualification_status": gate["qualification_status"],
        "next_action": gate["next_action"],
        "route": manual_route(),
        "pending_checks": list(gate["pending_checks"]),
        "evidence": list(payload.get("evidence", []))
        if isinstance(payload.get("evidence", []), list)
        else [],
        "reason": gate["reason"],
    }

    if gate["phase"] == "ADAPTATION" and gate["decision"] == "PROCEED":
        framework_route = resolve_route(gate, frameworks, framework_families)
        result["framework"] = framework_route["framework"]
        result["route"] = {
            "skill": framework_route["route_skill"],
            "source": "official"
            if framework_route["route_type"] == "OFFICIAL_SKILL"
            else "manual",
            "type": framework_route["route_type"],
            "analysis_skill": framework_route["analysis_skill"],
            "analysis_source": "official"
            if framework_route["analysis_skill"]
            else None,
            "official_repository": framework_route["official_repository"],
        }
        if framework_route["route_type"] == "MANUAL_REQUIRED":
            if framework_route["analysis_skill"]:
                result["next_action"] = (
                    f"先执行官方分析 Skill {framework_route['analysis_skill']}，"
                    "再基于分析结果人工完成实际适配实现；不得把分析 Skill 当成完整 porting 实现。"
                )
            else:
                result["next_action"] = (
                    "当前配置未确认官方实际适配实现 Skill；进入人工/交互式适配，"
                    "并保留真实代码、构建和验证证据。"
                )
        return result

    if (
        gate["phase"] == "QUALIFICATION"
        and gate["decision"] == "BLOCKED"
        and gate["qualification_status"] == "NEEDS_OFFICIAL_CHECK"
    ):
        framework_key = resolve_framework_key(
            gate["framework"],
            frameworks,
            framework_families,
        )
        framework_config = require_dict(
            frameworks[framework_key],
            f"frameworks.{framework_key}",
        )
        skills = require_dict(
            framework_config.get("official_skills", {}),
            f"frameworks.{framework_key}.official_skills",
        )
        matched_skill = find_pending_official_skill(gate["pending_checks"], skills)
        result["framework"] = framework_key
        if matched_skill:
            result["route"] = {
                "skill": matched_skill,
                "source": "official",
                "type": "QUALIFICATION_CHECK",
                "analysis_skill": None,
                "analysis_source": None,
                "official_repository": skills.get("repository"),
            }
        return result

    return result


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: resolve_next_action.py <qualification-json> <frameworks-yaml> <next-action-json>"
        )

    qualification_path = Path(sys.argv[1])
    frameworks_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    payload = json.loads(qualification_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("qualification artifact must be a JSON object")

    try:
        frameworks, framework_families = load_framework_config(frameworks_path)
        result = resolve_next_action(payload, frameworks, framework_families)
    except ValueError as exc:
        raise SystemExit(f"cannot resolve next action: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Next action: {result['candidate']} ({result['framework']}) -> "
        f"{result['phase']}/{result['decision']} / {result['route']['skill']}"
    )


if __name__ == "__main__":
    main()
