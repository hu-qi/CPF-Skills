from __future__ import annotations

import re
import sys
from pathlib import Path


EXPECTED = {
    "AlphaPlugin": "NEEDS_OFFICIAL_CHECK",
    "BetaPlugin": "EXCLUDED_ALREADY_ADAPTED",
    "GammaPackage": "EXCLUDED_NO_ADAPTATION_NEEDED",
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

    text = output_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        fail("Pi returned empty output")

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for candidate, expected_status in EXPECTED.items():
        matching_lines = [line for line in lines if candidate.lower() in line.lower()]
        if not matching_lines:
            fail(f"candidate {candidate} not found in output")

        if not any(expected_status in line for line in matching_lines):
            rendered = "\n".join(matching_lines)
            fail(
                f"{candidate} must be {expected_status}; matching output was:\n{rendered}"
            )

    alpha_lines = [line for line in lines if "alphaplugin" in line.lower()]
    if any(re.search(r"\bRECOMMENDED\b", line) for line in alpha_lines):
        fail("AlphaPlugin must not be marked RECOMMENDED while required checks are incomplete")

    print("CONTRACT PASSED: discovery state machine matches expected outcomes")


if __name__ == "__main__":
    main()
