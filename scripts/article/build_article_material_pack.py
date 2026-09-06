from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_VALIDATION_CHECKS = (
    "implementation",
    "build",
    "demo",
    "tests",
    "device_run",
    "screenshots",
)

FIXTURE_EVIDENCE_PREFIX = "fixture://"


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


def require_fixture_flag(payload: dict[str, Any], name: str) -> bool:
    value = payload.get("fixture_only", False)
    if not isinstance(value, bool):
        raise ValueError(f"{name}.fixture_only must be a boolean when provided")
    return value


def find_fixture_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, str):
        if value.startswith(FIXTURE_EVIDENCE_PREFIX):
            refs.append(value)
    elif isinstance(value, list):
        for item in value:
            refs.extend(find_fixture_refs(item))
    elif isinstance(value, dict):
        for item in value.values():
            refs.extend(find_fixture_refs(item))
    return refs


def validation_evidence(validation_gate: dict[str, Any]) -> dict[str, list[str]]:
    if validation_gate.get("phase") != "ARTICLE_PREP" or validation_gate.get("decision") != "PROCEED":
        raise ValueError("validation gate must be ARTICLE_PREP/PROCEED before building article materials")
    checks = require_dict(validation_gate.get("checks"), "validation_gate.checks")
    result: dict[str, list[str]] = {}
    for name in REQUIRED_VALIDATION_CHECKS:
        check = require_dict(checks.get(name), f"validation_gate.checks.{name}")
        if check.get("status") != "VERIFIED":
            raise ValueError(f"validation_gate.checks.{name} must be VERIFIED")
        evidence = require_string_list(
            check.get("evidence", []),
            f"validation_gate.checks.{name}.evidence",
        )
        if not evidence:
            raise ValueError(f"validation_gate.checks.{name} must contain evidence")
        result[name] = evidence
    return result


def build_material_pack(
    qualification: dict[str, Any],
    validation_gate: dict[str, Any],
    development_notes: dict[str, Any],
) -> dict[str, Any]:
    framework = qualification.get("framework")
    candidate = qualification.get("candidate")
    if not isinstance(framework, str) or not framework.strip():
        raise ValueError("qualification.framework must be a non-empty string")
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("qualification.candidate must be a non-empty string")
    if validation_gate.get("framework") != framework:
        raise ValueError("qualification and validation gate framework mismatch")
    if validation_gate.get("candidate") != candidate:
        raise ValueError("qualification and validation gate candidate mismatch")

    fixture_flags = {
        require_fixture_flag(qualification, "qualification"),
        require_fixture_flag(validation_gate, "validation_gate"),
        require_fixture_flag(development_notes, "development_notes"),
    }
    if len(fixture_flags) != 1:
        raise ValueError("qualification, validation gate and development notes fixture_only flags must match")
    fixture_only = fixture_flags.pop()

    if not fixture_only:
        fixture_refs = [
            *find_fixture_refs(qualification),
            *find_fixture_refs(validation_gate),
            *find_fixture_refs(development_notes),
        ]
        if fixture_refs:
            raise ValueError(
                "fixture:// evidence is test-only and cannot be used in real article materials"
            )

    qualification_body = require_dict(qualification.get("qualification"), "qualification.qualification")
    if qualification_body.get("status") != "RECOMMENDED":
        raise ValueError("article material pack requires qualification.status=RECOMMENDED")

    evidence = validation_evidence(validation_gate)

    notes = require_dict(development_notes, "development_notes")
    summary = notes.get("summary")
    if summary is not None and not isinstance(summary, str):
        raise ValueError("development_notes.summary must be a string")

    problems = require_list_of_dicts(notes.get("problems", []), "development_notes.problems")
    decisions = require_list_of_dicts(notes.get("decisions", []), "development_notes.decisions")
    api_changes = require_list_of_dicts(notes.get("api_changes", []), "development_notes.api_changes")

    source_refs = require_string_list(notes.get("source_refs", []), "development_notes.source_refs")

    sections = [
        {
            "section": "选库背景与适配必要性",
            "source": "qualification",
            "evidence": list(qualification.get("evidence", [])) if isinstance(qualification.get("evidence"), list) else [],
            "author_prompts": [
                "用作者自己的话解释为什么选择该库。",
                "说明活动去重与适配必要性是如何确认的。",
            ],
        },
        {
            "section": "适配环境与范围",
            "source": "development_notes + implementation/build evidence",
            "evidence": evidence["implementation"] + evidence["build"],
            "author_prompts": [
                "写明实际使用的框架/SDK/设备版本与适配边界。",
                "若使用兼容版本回退，说明原因。",
            ],
        },
        {
            "section": "核心适配实现",
            "source": "development_notes + implementation evidence",
            "evidence": evidence["implementation"],
            "author_prompts": [
                "基于真实 diff/commit 解释关键改动，不补写不存在的实现。",
                "优先说明平台差异、接口映射和行为对齐。",
            ],
        },
        {
            "section": "问题、尝试与解决过程",
            "source": "development_notes.problems/decisions",
            "evidence": source_refs,
            "author_prompts": [
                "只写真实发生的问题、失败尝试和最终选择。",
                "没有记录的问题不要为了文章完整性而虚构。",
            ],
        },
        {
            "section": "Demo、测试与真机验证",
            "source": "validation",
            "evidence": evidence["demo"] + evidence["tests"] + evidence["device_run"] + evidence["screenshots"],
            "author_prompts": [
                "说明 Demo 场景、关键测试结果和实体设备验证过程。",
                "把成功运行截图放在对应验证步骤附近。",
            ],
        },
        {
            "section": "总结与可复用经验",
            "source": "author synthesis",
            "evidence": source_refs,
            "author_prompts": [
                "由作者总结适配经验、局限和后续工作。",
                "不要让 AI 凭空生成未经历的经验。",
            ],
        },
    ]

    gaps: list[str] = []
    if not problems:
        gaps.append("development_notes.problems 为空：问题过程章节只能由作者补充真实记录，不能虚构。")
    if not decisions:
        gaps.append("development_notes.decisions 为空：关键技术取舍需要作者提供真实依据。")
    if not api_changes:
        gaps.append("development_notes.api_changes 为空：如存在接口/行为变化，应补充真实记录。")
    if not source_refs:
        gaps.append("development_notes.source_refs 为空：建议补充 commit/diff/log/issue 等可审计引用。")

    return {
        "schema_version": 1,
        "fixture_only": fixture_only,
        "framework": framework,
        "candidate": candidate,
        "qualification_status": qualification_body.get("status"),
        "validation_status": "ARTICLE_PREP/PROCEED",
        "development_summary": summary or "",
        "problems": problems,
        "decisions": decisions,
        "api_changes": api_changes,
        "source_refs": source_refs,
        "validation_evidence": evidence,
        "section_plan": sections,
        "material_gaps": gaps,
        "ai_boundary": {
            "full_article_generation_allowed": False,
            "allowed_assistance": [
                "证据整理",
                "提纲生成",
                "章节要点映射",
                "局部改写/润色",
                "规则检查",
            ],
            "author_required": [
                "主体实践叙述",
                "真实问题与失败尝试",
                "个人技术取舍与经验总结",
                "原创性与 AI 占比确认",
            ],
        },
    }


def require_list_of_dicts(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        result.append(require_dict(item, f"{name}[{index}]"))
    return result


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: build_article_material_pack.py <qualification-json> <validation-gate-json> "
            "<development-notes-json> <material-pack-json>"
        )

    qualification_path = Path(sys.argv[1])
    validation_path = Path(sys.argv[2])
    notes_path = Path(sys.argv[3])
    output_path = Path(sys.argv[4])

    qualification = require_dict(json.loads(qualification_path.read_text(encoding="utf-8")), "qualification")
    validation_gate = require_dict(json.loads(validation_path.read_text(encoding="utf-8")), "validation gate")
    development_notes = require_dict(json.loads(notes_path.read_text(encoding="utf-8")), "development notes")

    try:
        pack = build_material_pack(qualification, validation_gate, development_notes)
    except ValueError as exc:
        raise SystemExit(f"cannot build article material pack: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Article material pack: {pack['candidate']} -> "
        f"sections={len(pack['section_plan'])}, gaps={len(pack['material_gaps'])}"
    )


if __name__ == "__main__":
    main()
