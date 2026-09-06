from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


PROCEED_PHASE = "ADAPTATION"
PROCEED_DECISION = "PROCEED"


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def load_frameworks(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = require_dict(data, "framework config")
    frameworks = require_dict(root.get("frameworks"), "frameworks")
    return frameworks


def resolve_framework_key(framework: str, frameworks: dict[str, Any]) -> str:
    wanted = framework.strip().lower()
    if not wanted:
        raise ValueError("framework must be a non-empty string")

    for key, raw in frameworks.items():
        config = require_dict(raw, f"frameworks.{key}")
        aliases = config.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
            raise ValueError(f"frameworks.{key}.aliases must be a string list")
        names = {str(key).lower(), *(item.lower() for item in aliases)}
        if wanted in names:
            return str(key)

    raise ValueError(f"unsupported framework: {framework!r}")


def resolve_route(gate: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    framework = gate.get("framework")
    candidate = gate.get("candidate")
    phase = gate.get("phase")
    decision = gate.get("decision")

    if not isinstance(framework, str) or not framework.strip():
        raise ValueError("gate.framework must be a non-empty string")
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("gate.candidate must be a non-empty string")
    if not isinstance(phase, str) or not isinstance(decision, str):
        raise ValueError("gate.phase and gate.decision must be strings")

    key = resolve_framework_key(framework, frameworks)
    framework_config = require_dict(frameworks[key], f"frameworks.{key}")
    skills = require_dict(framework_config.get("official_skills", {}), f"frameworks.{key}.official_skills")

    result: dict[str, Any] = {
        "schema_version": 1,
        "framework": key,
        "candidate": candidate,
        "gate_phase": phase,
        "gate_decision": decision,
        "route_type": None,
        "route_skill": None,
        "analysis_skill": None,
        "official_repository": skills.get("repository"),
        "reason": "",
    }

    # The route resolver cannot override qualification gating.
    if phase != PROCEED_PHASE or decision != PROCEED_DECISION:
        result.update(
            {
                "route_type": "BLOCKED_BY_GATE",
                "reason": "qualification gate 未进入 ADAPTATION/PROCEED；禁止解析实际适配路由。",
            }
        )
        return result

    analysis_skill = skills.get("migration_analyzer")
    if analysis_skill is not None and not isinstance(analysis_skill, str):
        raise ValueError(f"frameworks.{key}.official_skills.migration_analyzer must be string or null")
    implementation = skills.get("adaptation_implementation")
    if implementation is not None and not isinstance(implementation, str):
        raise ValueError(f"frameworks.{key}.official_skills.adaptation_implementation must be string or null")

    result["analysis_skill"] = analysis_skill

    if implementation:
        result.update(
            {
                "route_type": "OFFICIAL_SKILL",
                "route_skill": implementation,
                "reason": "当前框架配置已审计并显式声明实际适配实现 Skill。",
            }
        )
        return result

    result.update(
        {
            "route_type": "MANUAL_REQUIRED",
            "route_skill": None,
            "reason": "当前框架配置未确认独立的实际适配实现 Skill；可以使用已确认分析/检查 Skill，但实现阶段必须人工或等待后续审计。",
        }
    )
    return result


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: resolve_framework_route.py <gate-json> <frameworks-yaml> <route-json>"
        )

    gate_path = Path(sys.argv[1])
    frameworks_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if not isinstance(gate, dict):
        raise SystemExit("gate artifact must be a JSON object")

    try:
        route = resolve_route(gate, load_frameworks(frameworks_path))
    except ValueError as exc:
        raise SystemExit(f"cannot resolve framework route: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(route, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Framework route: {route['candidate']} ({route['framework']}) -> "
        f"{route['route_type']} / {route['route_skill']}"
    )


if __name__ == "__main__":
    main()
