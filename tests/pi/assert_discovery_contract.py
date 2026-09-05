from __future__ import annotations

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


def normalize_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def parse_candidate_statuses(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue

        cells = [normalize_cell(cell) for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue

        candidate, status = cells[0], cells[1]
        if candidate in EXPECTED:
            rows[candidate] = status

    return rows


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: assert_discovery_contract.py <pi-output-file>")

    output_path = Path(sys.argv[1])
    if not output_path.exists():
        fail(f"missing output file: {output_path}")

    text = output_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        fail("Pi returned empty output")

    rows = parse_candidate_statuses(text)

    for candidate, expected_status in EXPECTED.items():
        if candidate not in rows:
            fail(f"candidate {candidate} not found in a Markdown table row")

        actual_status = rows[candidate]
        if actual_status not in ALLOWED_STATUSES:
            fail(
                f"{candidate} returned non-canonical status token {actual_status!r}; "
                f"allowed={sorted(ALLOWED_STATUSES)}"
            )

        if actual_status != expected_status:
            fail(
                f"{candidate} must be {expected_status}; actual status was {actual_status}"
            )

    print("CONTRACT PASSED: discovery state machine matches expected outcomes")


if __name__ == "__main__":
    main()
