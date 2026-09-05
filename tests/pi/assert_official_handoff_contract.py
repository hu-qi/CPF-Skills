from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EXPECTED = {
    "ReadyPlugin": "RECOMMENDED",
    "ExistingPlugin": "EXCLUDED_ALREADY_ADAPTED",
    "PureDartPackage": "EXCLUDED_NO_ADAPTATION_NEEDED",
    "PartialCheckPlugin": "NEEDS_OFFICIAL_CHECK",
}

ALLOWED_STATUSES = {
    "RECOMMENDED",
    "NEEDS_OFFICIAL_CHECK",
    "EXCLUDED_ALREADY_ADAPTED",
    "EXCLUDED_NO_ADAPTATION_NEEDED",
    "EXCLUDED_LOW_VALUE",
    "EXCLUDED_UNVERIFIABLE",
}


def fail(message: str) -> None:
    print(f"HANDOFF CONTRACT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_json(text: str) -> dict:
    text = text.strip()
    if not text:
        fail("Pi returned empty output")

    if text.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
        if not match:
            fail("fenced output must contain exactly one JSON object")
        text = match.group(1)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")

    if not isinstance(payload, dict):
        fail("top-level output must be a JSON object")
    return payload


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: assert_official_handoff_contract.py <pi-output-file>")

    output_path = Path(sys.argv[1])
    if not output_path.exists():
        fail(f"missing output file: {output_path}")

    payload = parse_json(output_path.read_text(encoding="utf-8", errors="replace"))
    if set(payload) != {"results"}:
        fail("top-level JSON must contain only 'results'")

    results = payload["results"]
    if not isinstance(results, list) or len(results) != len(EXPECTED):
        fail(f"results must contain exactly {len(EXPECTED)} items")

    actual: dict[str, str] = {}
    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict) or set(item) != {"candidate", "status", "reason"}:
            fail(f"result #{index} must contain candidate/status/reason only")

        candidate = item["candidate"]
        status = item["status"]
        reason = item["reason"]

        if candidate not in EXPECTED:
            fail(f"unexpected candidate {candidate!r}")
        if candidate in actual:
            fail(f"duplicate candidate {candidate}")
        if status not in ALLOWED_STATUSES:
            fail(f"{candidate}: invalid status token {status!r}")
        if not isinstance(reason, str) or not reason.strip():
            fail(f"{candidate}: reason must be non-empty")

        actual[candidate] = status

    if set(actual) != set(EXPECTED):
        fail("candidate set mismatch")

    for candidate, expected_status in EXPECTED.items():
        if actual[candidate] != expected_status:
            fail(f"{candidate} must be {expected_status}; actual={actual[candidate]}")

    print("HANDOFF CONTRACT PASSED: official Skill results map to discovery states correctly")


if __name__ == "__main__":
    main()
