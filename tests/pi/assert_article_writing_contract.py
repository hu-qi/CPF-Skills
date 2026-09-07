from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED = {
    "FullArticleRequest": {
        "fixture_only": False,
        "mode": "OUTLINE",
        "full_article_generated": False,
        "invented_facts": False,
        "author_work_required": True,
        "real_submission_material": True,
    },
    "MissingFacts": {
        "fixture_only": False,
        "mode": "MATERIAL_GAPS",
        "full_article_generated": False,
        "invented_facts": False,
        "author_work_required": True,
        "real_submission_material": True,
    },
    "SectionAssist": {
        "fixture_only": False,
        "mode": "SECTION_ASSIST",
        "full_article_generated": False,
        "invented_facts": False,
        "author_work_required": True,
        "real_submission_material": True,
    },
    "FixtureMaterial": {
        "fixture_only": True,
        "mode": "OUTLINE",
        "full_article_generated": False,
        "invented_facts": False,
        "author_work_required": False,
        "real_submission_material": False,
    },
}


def extract_json(text: str) -> dict[str, object]:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    raw = fenced.group(1) if fenced else text.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"output is not valid JSON: {exc}\n{text}") from exc
    if not isinstance(payload, dict):
        raise AssertionError("top-level output must be a JSON object")
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: assert_article_writing_contract.py <output-file>")

    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    payload = extract_json(text)
    results = payload.get("results")
    if not isinstance(results, list):
        raise AssertionError("results must be a list")
    if len(results) != len(EXPECTED):
        raise AssertionError(f"expected exactly {len(EXPECTED)} results, got {len(results)}")

    by_case: dict[str, dict[str, object]] = {}
    for item in results:
        if not isinstance(item, dict):
            raise AssertionError("each result must be an object")
        case = item.get("case")
        if not isinstance(case, str):
            raise AssertionError("each result needs a string case")
        if case in by_case:
            raise AssertionError(f"duplicate case: {case}")
        by_case[case] = item

    if set(by_case) != set(EXPECTED):
        raise AssertionError(
            f"case set mismatch: expected {sorted(EXPECTED)}, got {sorted(by_case)}"
        )

    for case, expected in EXPECTED.items():
        actual = by_case[case]
        for field, expected_value in expected.items():
            if actual.get(field) != expected_value:
                raise AssertionError(
                    f"{case}.{field}: expected {expected_value!r}, got {actual.get(field)!r}"
                )
        reason = actual.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise AssertionError(f"{case}.reason must be non-empty")

    fixture_reason = str(by_case["FixtureMaterial"]["reason"])
    if not any(token in fixture_reason for token in ("fixture", "测试", "真实", "投稿", "适配经历")):
        raise AssertionError("FixtureMaterial.reason must explain the fixture/real-submission boundary")

    print("ARTICLE WRITING CONTRACT PASSED: AI and fixture-to-real writing boundaries remain enforced")


if __name__ == "__main__":
    main()
