from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CANONICAL_STATUSES = {
    "RECOMMENDED",
    "NEEDS_OFFICIAL_CHECK",
    "EXCLUDED_ALREADY_ADAPTED",
    "EXCLUDED_NO_ADAPTATION_NEEDED",
    "EXCLUDED_LOW_VALUE",
    "EXCLUDED_UNVERIFIABLE",
}

LIBRARY_SEARCH_RESULTS = {
    "adapted",
    "needs_adaptation",
    "no_adaptation_needed",
    "inconclusive",
    "not_run",
}

NECESSITY_RESULTS = {
    "needed",
    "not_needed",
    "inconclusive",
    "not_run",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def find_candidate(discovery: dict[str, Any], name: str) -> dict[str, Any] | None:
    candidates = discovery.get("candidates")
    if not isinstance(candidates, list):
        return None
    for item in candidates:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    return None


def normalize_dedup_sources(discovery: dict[str, Any]) -> list[dict[str, Any]]:
    checked = discovery.get("checked_sources")
    if not isinstance(checked, list):
        return []

    result: list[dict[str, Any]] = []
    for item in checked:
        if not isinstance(item, dict):
            continue
        if not item.get("required"):
            continue
        result.append(
            {
                "name": item.get("name"),
                "url": item.get("url"),
                "required": True,
                "result": item.get("result", "unknown"),
                "note": item.get("note"),
                "error": item.get("error"),
            }
        )
    return result


def normalize_matches(candidate: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not candidate:
        return []
    matches = candidate.get("dedup_matches")
    if not isinstance(matches, list):
        return []
    return [item for item in matches if isinstance(item, dict)]


def default_official_checks() -> dict[str, Any]:
    return {
        "library_search": {
            "skill": "flutter-library-search",
            "result": "not_run",
            "evidence": [],
            "reason": "官方库搜索尚未执行。",
            "pending_checks": ["执行 flutter-library-search"],
        },
        "adaptation_necessity": {
            "skill": "ohos-flutter-plugin-adaptation-necessity-check",
            "result": "not_run",
            "evidence": [],
            "reason": "源码级适配必要性检查尚未执行。",
        },
    }


def normalize_official_checks(
    candidate_name: str,
    handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    if handoff is None:
        return default_official_checks()

    if handoff.get("candidate") != candidate_name:
        raise ValueError(
            f"official handoff candidate mismatch: expected={candidate_name!r}, "
            f"actual={handoff.get('candidate')!r}"
        )

    raw = handoff.get("official_checks")
    if not isinstance(raw, dict):
        raise ValueError("official handoff must contain official_checks")

    default = default_official_checks()
    result: dict[str, Any] = {}
    for key in ("library_search", "adaptation_necessity"):
        item = raw.get(key)
        if not isinstance(item, dict):
            result[key] = default[key]
            continue
        result[key] = item

    library_result = result["library_search"].get("result")
    necessity_result = result["adaptation_necessity"].get("result")
    if library_result not in LIBRARY_SEARCH_RESULTS:
        raise ValueError(f"invalid library_search result: {library_result!r}")
    if necessity_result not in NECESSITY_RESULTS:
        raise ValueError(f"invalid adaptation_necessity result: {necessity_result!r}")
    return result


def pending_from_official(checks: dict[str, Any]) -> list[str]:
    pending: list[str] = []
    for key in ("library_search", "adaptation_necessity"):
        item = checks.get(key)
        if not isinstance(item, dict):
            continue
        raw = item.get("pending_checks")
        if isinstance(raw, list):
            pending.extend(str(value) for value in raw if isinstance(value, str) and value.strip())
    return list(dict.fromkeys(pending))


def qualify(
    *,
    candidate_name: str,
    candidate: dict[str, Any] | None,
    dedup_sources: list[dict[str, Any]],
    dedup_matches: list[dict[str, Any]],
    official_checks: dict[str, Any],
) -> tuple[str, str, list[str]]:
    if candidate is None:
        return (
            "EXCLUDED_UNVERIFIABLE",
            "候选不在 discovery evidence 中，无法验证其包身份和发现证据。",
            ["重新执行候选发现并确认包名"],
        )

    library_search = official_checks.get("library_search")
    necessity = official_checks.get("adaptation_necessity")
    library_result = library_search.get("result") if isinstance(library_search, dict) else "not_run"
    necessity_result = necessity.get("result") if isinstance(necessity, dict) else "not_run"

    # Positive exclusion facts take precedence over incomplete absence checks.
    if library_result == "adapted":
        return (
            "EXCLUDED_ALREADY_ADAPTED",
            "CPF-Flutter 官方库搜索已确认存在可用鸿蒙适配。",
            [],
        )

    if library_result == "no_adaptation_needed" or necessity_result == "not_needed":
        return (
            "EXCLUDED_NO_ADAPTATION_NEEDED",
            "官方技术检查已确认该库不需要鸿蒙平台适配。",
            [],
        )

    if dedup_matches:
        match_summary = ", ".join(
            f"{item.get('source')}: {item.get('match')}" for item in dedup_matches[:5]
        )
        return (
            "EXCLUDED_ALREADY_ADAPTED",
            f"活动去重源存在同库或等价实现命中：{match_summary}",
            [],
        )

    incomplete_sources = [
        item for item in dedup_sources if item.get("result") != "checked"
    ]
    if incomplete_sources:
        names = ", ".join(
            f"{item.get('name')}={item.get('result')}" for item in incomplete_sources
        )
        pending = [f"补全 required 去重源：{names}"]
        pending.extend(pending_from_official(official_checks))
        return (
            "NEEDS_OFFICIAL_CHECK",
            f"活动 required 去重尚未全部完成：{names}。在此之前不得升级为 RECOMMENDED。",
            list(dict.fromkeys(pending)),
        )

    technical_needed = library_result == "needs_adaptation" or necessity_result == "needed"
    if technical_needed:
        return (
            "RECOMMENDED",
            "官方技术结论表明需要鸿蒙适配，且所有 required 活动去重源均已检查并无明确命中。",
            [],
        )

    pending = pending_from_official(official_checks)
    if library_result in {"inconclusive", "not_run"}:
        if not pending:
            pending.append("完成或复核 flutter-library-search")
        return (
            "NEEDS_OFFICIAL_CHECK",
            f"官方库搜索当前为 {library_result}，技术必要性尚未形成可用于推荐的确定结论。",
            pending,
        )

    if necessity_result in {"inconclusive", "not_run"}:
        if not pending:
            pending.append("按需执行源码级适配必要性检查")
        return (
            "NEEDS_OFFICIAL_CHECK",
            f"源码级适配必要性当前为 {necessity_result}，尚不足以升级为 RECOMMENDED。",
            pending,
        )

    return (
        "EXCLUDED_UNVERIFIABLE",
        "输入结论组合无法映射到规范资格状态。",
        ["检查 official handoff 与 discovery evidence 是否匹配"],
    )


def build_artifact(
    *,
    framework: str,
    candidate_name: str,
    discovery: dict[str, Any],
    handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    if framework != "flutter":
        raise ValueError("v0.1 qualification builder currently supports framework=flutter only")

    evidence_framework = discovery.get("framework")
    if evidence_framework not in {None, framework}:
        raise ValueError(
            f"discovery framework mismatch: expected={framework!r}, actual={evidence_framework!r}"
        )

    candidate = find_candidate(discovery, candidate_name)
    dedup_sources = normalize_dedup_sources(discovery)
    dedup_matches = normalize_matches(candidate)
    checks = normalize_official_checks(candidate_name, handoff)
    status, reason, pending = qualify(
        candidate_name=candidate_name,
        candidate=candidate,
        dedup_sources=dedup_sources,
        dedup_matches=dedup_matches,
        official_checks=checks,
    )
    if status not in CANONICAL_STATUSES:
        raise AssertionError(f"non-canonical status produced: {status}")

    return {
        "schema_version": 1,
        "framework": framework,
        "candidate": candidate_name,
        "discovery": {
            "candidate": candidate,
        },
        "activity_dedup": {
            "required_sources": dedup_sources,
            "matches": dedup_matches,
            "all_required_checked": bool(dedup_sources)
            and all(item.get("result") == "checked" for item in dedup_sources),
        },
        "official_checks": checks,
        "qualification": {
            "status": status,
            "eligible_to_start_adaptation": status == "RECOMMENDED",
            "reason": reason,
            "pending_checks": pending,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic candidate qualification artifact")
    parser.add_argument("--framework", default="flutter")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--discovery-evidence", type=Path, required=True)
    parser.add_argument("--official-handoff", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    discovery = load_json(args.discovery_evidence)
    handoff = load_json(args.official_handoff) if args.official_handoff else None
    artifact = build_artifact(
        framework=args.framework,
        candidate_name=args.candidate,
        discovery=discovery,
        handoff=handoff,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Qualification: {args.candidate} -> "
        f"{artifact['qualification']['status']}"
    )


if __name__ == "__main__":
    main()
