from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED = {
    "ReadyPlugin": {
        "phase": "ADAPTATION",
        "decision": "PROCEED",
        "qualification_status": "RECOMMENDED",
        "route_skill": None,
    },
    "NeedsCheckPlugin": {
        "phase": "QUALIFICATION",
        "decision": "BLOCKED",
        "qualification_status": "NEEDS_OFFICIAL_CHECK",
        "route_skill": "flutter-library-search",
    },
    "ExistingPlugin": {
        "phase": "STOPPED",
        "decision": "STOP",
        "qualification_status": "EXCLUDED_ALREADY_ADAPTED",
        "route_skill": None,
    },
    "PureDartPackage": {
        "phase": "STOPPED",
        "decision": "STOP",
        "qualification_status": "EXCLUDED_NO_ADAPTATION_NEEDED",
        "route_skill": None,
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
        raise SystemExit("usage: assert_orchestrator_contract.py <output-file>")

    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    payload = extract_json(text)
    results = payload.get("results")
    if not isinstance(results, list):
        raise AssertionError("results must be a list")
    if len(results) != 4:
        raise AssertionError(f"expected exactly 4 results, got {len(results)}")

    by_candidate: dict[str, dict[str, object]] = {}
    for item in results:
        if not isinstance(item, dict):
            raise AssertionError("each result must be an object")
        candidate = item.get("candidate")
        if not isinstance(candidate, str):
            raise AssertionError("each result needs a string candidate")
        if candidate in by_candidate:
            raise AssertionError(f"duplicate candidate: {candidate}")
        by_candidate[candidate] = item

    if set(by_candidate) != set(EXPECTED):
        raise AssertionError(
            f"candidate set mismatch: expected {sorted(EXPECTED)}, got {sorted(by_candidate)}"
        )

    for candidate, expected in EXPECTED.items():
        actual = by_candidate[candidate]
        for field, expected_value in expected.items():
            if actual.get(field) != expected_value:
                raise AssertionError(
                    f"{candidate}.{field}: expected {expected_value!r}, got {actual.get(field)!r}"
                )
        reason = actual.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise AssertionError(f"{candidate}.reason must be non-empty")

    print("ORCHESTRATOR CONTRACT PASSED: qualification gates and routing are stable")


if __name__ == "__main__":
    main()
