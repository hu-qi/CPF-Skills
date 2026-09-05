from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ALLOWED_RESULTS = {
    "adapted",
    "needs_adaptation",
    "no_adaptation_needed",
    "inconclusive",
}

MARKER = "<!-- OFFICIAL_RESULT -->"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def extract_result(text: str) -> dict[str, Any] | None:
    if MARKER not in text:
        return None
    tail = text.split(MARKER, 1)[1].strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", tail, flags=re.S)
    raw = match.group(1) if match else None
    if raw is None:
        direct = re.search(r"(\{.*\})", tail, flags=re.S)
        raw = direct.group(1) if direct else None
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def evidence_urls(evidence: dict[str, Any]) -> list[str]:
    urls: list[str] = []

    pub = evidence.get("pub_dev")
    if isinstance(pub, dict):
        source = pub.get("source")
        if isinstance(source, dict) and isinstance(source.get("url"), str):
            urls.append(source["url"])
        package = pub.get("package")
        if isinstance(package, dict) and isinstance(package.get("repository"), str):
            urls.append(package["repository"])

    origin = evidence.get("origin_repository")
    if isinstance(origin, dict):
        repo = origin.get("repository")
        if isinstance(repo, dict) and isinstance(repo.get("html_url"), str):
            urls.append(repo["html_url"])

    searches = evidence.get("cross_platform_searches")
    if isinstance(searches, list):
        for item in searches:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                urls.append(item["url"])

    unique: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def source_gaps(evidence: dict[str, Any]) -> list[str]:
    gaps: list[str] = []

    def inspect(name: str, source: Any) -> None:
        if not isinstance(source, dict):
            gaps.append(f"{name}: missing")
            return
        result = source.get("result")
        if result not in {"checked"}:
            gaps.append(f"{name}: {result or 'unknown'}")

    pub = evidence.get("pub_dev")
    inspect("pub.dev", pub.get("source") if isinstance(pub, dict) else None)
    origin = evidence.get("origin_repository")
    inspect("origin_repository", origin.get("source") if isinstance(origin, dict) else None)

    searches = evidence.get("cross_platform_searches")
    if isinstance(searches, list):
        for item in searches:
            if isinstance(item, dict):
                inspect(str(item.get("name") or "cross_platform_search"), item)
            else:
                gaps.append("cross_platform_search: malformed")
    else:
        gaps.append("cross_platform_searches: missing")
    return gaps


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: normalize_official_flutter_result.py "
            "<candidate> <pi-exit> <evidence-json> <pi-output> <output-json>"
        )

    candidate = sys.argv[1]
    try:
        pi_exit = int(sys.argv[2])
    except ValueError:
        pi_exit = -1

    evidence_path = Path(sys.argv[3])
    output_path = Path(sys.argv[4])
    normalized_path = Path(sys.argv[5])

    evidence = read_json(evidence_path) if evidence_path.exists() else {}
    text = output_path.read_text(encoding="utf-8", errors="replace") if output_path.exists() else ""
    raw = extract_result(text)
    gaps = source_gaps(evidence)

    result = "inconclusive"
    reason = "官方 Skill 未产生可解析的机器结果。"
    pending: list[str] = []
    urls = evidence_urls(evidence)

    if pi_exit == 124:
        reason = "官方 Skill 判断阶段达到 CI 时间上限。"
        pending.append("在交互环境或更完整的证据条件下重新执行 flutter-library-search")
    elif pi_exit != 0:
        reason = f"官方 Skill 判断阶段异常退出（exit={pi_exit}）。"
        pending.append("检查 Pi/provider 日志并重新执行官方 Skill")
    elif raw is not None:
        raw_candidate = raw.get("candidate")
        raw_skill = raw.get("skill")
        raw_result = raw.get("result")
        raw_reason = raw.get("reason")
        raw_urls = raw.get("evidence_urls")
        raw_pending = raw.get("pending_checks")

        valid = (
            raw_candidate == candidate
            and raw_skill == "flutter-library-search"
            and raw_result in ALLOWED_RESULTS
            and isinstance(raw_reason, str)
            and raw_reason.strip()
            and isinstance(raw_urls, list)
            and all(isinstance(url, str) for url in raw_urls)
            and isinstance(raw_pending, list)
            and all(isinstance(item, str) for item in raw_pending)
        )
        if valid:
            result = str(raw_result)
            reason = raw_reason.strip()
            urls = list(dict.fromkeys([*raw_urls, *urls]))
            pending = list(raw_pending)
        else:
            reason = "官方 Skill 返回了机器区块，但字段或枚举不符合 handoff 契约。"
            pending.append("检查 flutter-library-search 输出契约")

    if gaps and result != "inconclusive":
        # Conservative guardrail: the judge may explain why a partial source is not
        # material, but this generic normalizer must never silently strengthen facts.
        result = "inconclusive"
        reason = f"存在未完整核查的关键来源：{', '.join(gaps)}。原判断不得直接升级为确定结论。"
        pending.extend(gaps)

    normalized = {
        "candidate": candidate,
        "official_checks": {
            "library_search": {
                "skill": "flutter-library-search",
                "result": result,
                "evidence": urls,
                "reason": reason,
                "pending_checks": list(dict.fromkeys(pending)),
                "pi_exit": pi_exit,
            },
            "adaptation_necessity": {
                "skill": "ohos-flutter-plugin-adaptation-necessity-check",
                "result": "not_run",
                "evidence": [],
                "reason": "本阶段仅执行官方库搜索；源码级必要性检查按需执行。",
            },
        },
    }

    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Normalized official Flutter result: {candidate} -> {result}")


if __name__ == "__main__":
    main()
