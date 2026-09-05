from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED = {
    "AlphaPlugin": "NEEDS_OFFICIAL_CHECK",
    "BetaPlugin": "EXCLUDED_ALREADY_ADAPTED",
    "GammaPackage": "EXCLUDED_NO_ADAPTATION_NEEDED",
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
    print(f"CONTRACT FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: assert_discovery_contract.py <pi-output-file>")

    output_path = Path(sys.argv[1])
    if not output_path.exists():
        fail(f"missing output file: {output_path}")

    text = output_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        fail("Pi returned empty output")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"output must be a single JSON object: {exc}")

    if not isinstance(payload, dict) or set(payload) != {"results"}:
        fail("top-level JSON must contain only the 'results' field")

    results = payload.get("results")
    if not isinstance(results, list) or len(results) != len(EXPECTED):
        fail(f"results must contain exactly {len(EXPECTED)} items")

    actual: dict[str, str] = {}
    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            fail(f"result #{index} must be an object")
        if set(item) != {"candidate", "status", "reason"}:
            fail(f"result #{index} must contain candidate/status/reason only")

        candidate = item.get("candidate")
        status = item.get("status")
        reason = item.get("reason")

        if not isinstance(candidate, str) or candidate not in EXPECTED:
            fail(f"unexpected candidate {candidate!r}")
        if candidate in actual:
            fail(f"duplicate candidate {candidate}")
        if status not in ALLOWED_STATUSES:
            fail(f"{candidate}: invalid status token {status!r}")
        if not isinstance(reason, str) or not reason.strip():
            fail(f"{candidate}: reason must be a non-empty string")

        actual[candidate] = status

    if set(actual) != set(EXPECTED):
        fail(f"candidate set mismatch: actual={sorted(actual)} expected={sorted(EXPECTED)}")

    for candidate, expected_status in EXPECTED.items():
        if actual[candidate] != expected_status:
            fail(
                f"{candidate} must be {expected_status}; actual status was {actual[candidate]}"
            )

    print("CONTRACT PASSED: discovery state machine matches expected outcomes")


if __name__ == "__main__":
    main()
