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


def require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a string list")
    return value


def load_framework_config(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = require_dict(data, "framework config")
    frameworks = require_dict(root.get("frameworks"), "frameworks")
    families = require_dict(root.get("framework_families", {}), "framework_families")
    return frameworks, families


def load_frameworks(path: Path) -> dict[str, Any]:
    frameworks, _ = load_framework_config(path)
    return frameworks


def resolve_framework_key(
    framework: str,
    frameworks: dict[str, Any],
    framework_families: dict[str, Any] | None = None,
) -> str:
    wanted = framework.strip().lower()
    if not wanted:
        raise ValueError("framework must be a non-empty string")

    families = framework_families or {}
    for family_key, raw in families.items():
        config = require_dict(raw, f"framework_families.{family_key}")
        aliases = require_string_list(
            config.get("aliases", []),
            f"framework_families.{family_key}.aliases",
        )
        names = {str(family_key).lower(), *(item.lower() for item in aliases)}
        if wanted not in names:
            continue

        variants = require_string_list(
            config.get("variants", []),
            f"framework_families.{family_key}.variants",
        )
        if not variants:
            raise ValueError(
                f"framework family {family_key!r} must declare at least one variant"
            )
        unknown_variants = [variant for variant in variants if variant not in frameworks]
        if unknown_variants:
            raise ValueError(
                f"framework family {family_key!r} references unsupported variants: "
                + ", ".join(unknown_variants)
            )
        raise ValueError(
            f"ambiguous framework family: {framework!r}; choose one of: "
            + ", ".join(variants)
        )

    matches: list[str] = []
    for key, raw in frameworks.items():
        config = require_dict(raw, f"frameworks.{key}")
        aliases = require_string_list(config.get("aliases", []), f"frameworks.{key}.aliases")
        names = {str(key).lower(), *(item.lower() for item in aliases)}
        if wanted in names:
            matches.append(str(key))

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"ambiguous framework alias: {framework!r}; matches: "
            + ", ".join(matches)
        )
    raise ValueError(f"unsupported framework: {framework!r}")


def resolve_route(
    gate: dict[str, Any],
    frameworks: dict[str, Any],
    framework_families: dict[str, Any] | None = None,
) -> dict[str, Any]:
    framework = gate.get("framework")
    candidate = gate.get("candidate")
    phase = gate.get("phase")
    decision = gate.get("decision")
    fixture_only = gate.get("fixture_only", False)

    if not isinstance(framework, str) or not framework.strip():
        raise ValueError("gate.framework must be a non-empty string")
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("gate.candidate must be a non-empty string")
    if not isinstance(phase, str) or not isinstance(decision, str):
        raise ValueError("gate.phase and gate.decision must be strings")
    if not isinstance(fixture_only, bool):
        raise ValueError("gate.fixture_only must be a boolean when provided")

    key = resolve_framework_key(framework, frameworks, framework_families)
    framework_config = require_dict(frameworks[key], f"frameworks.{key}")
    skills = require_dict(framework_config.get("official_skills", {}), f"frameworks.{key}.official_skills")

    result: dict[str, Any] = {
        "schema_version": 1,
        "fixture_only": fixture_only,
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

    if fixture_only:
        result.update(
            {
                "route_type": "BLOCKED_BY_GATE",
                "reason": "fixture_only gate 仅用于回归覆盖，不解析或执行真实适配路由。",
            }
        )
        return result

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
        frameworks, framework_families = load_framework_config(frameworks_path)
        route = resolve_route(gate, frameworks, framework_families)
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
