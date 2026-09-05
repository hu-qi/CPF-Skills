from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_STATUSES = {
    "RECOMMENDED",
    "NEEDS_OFFICIAL_CHECK",
    "EXCLUDED_ALREADY_ADAPTED",
    "EXCLUDED_NO_ADAPTATION_NEEDED",
    "EXCLUDED_LOW_VALUE",
    "EXCLUDED_UNVERIFIABLE",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_SOURCE_RESULTS = {"checked", "partial", "unavailable"}


def fail(message: str) -> None:
    print(f"LIVE E2E FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def valid_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_ci_result(text: str) -> dict:
    marker = "<!-- CI_RESULT -->"
    if marker not in text:
        fail("missing <!-- CI_RESULT --> marker")

    tail = text.split(marker, 1)[1]
    match = re.search(r"```json\s*(\{.*?\})\s*```", tail, flags=re.DOTALL)
    if not match:
        fail("missing JSON code block after CI_RESULT marker")

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        fail(f"invalid CI_RESULT JSON: {exc}")

    if not isinstance(data, dict):
        fail("CI_RESULT must be a JSON object")
    return data


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: assert_flutter_discovery.py <pi-output-file>")

    output_path = Path(sys.argv[1])
    if not output_path.exists():
        fail(f"missing output file: {output_path}")

    text = output_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        fail("Pi returned empty output")

    data = extract_ci_result(text)

    if data.get("framework") != "flutter":
        fail(f"framework must be 'flutter', got {data.get('framework')!r}")

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not (3 <= len(candidates) <= 5):
        fail("candidates must contain between 3 and 5 items")

    names: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            fail(f"candidate #{index} must be an object")

        name = candidate.get("name")
        if not isinstance(name, str) or not name.strip():
            fail(f"candidate #{index} has invalid name")
        if name in names:
            fail(f"duplicate candidate name: {name}")
        names.add(name)

        status = candidate.get("status")
        if status not in ALLOWED_STATUSES:
            fail(f"{name}: invalid status {status!r}")

        difficulty = candidate.get("difficulty")
        if difficulty not in ALLOWED_DIFFICULTIES:
            fail(f"{name}: invalid difficulty {difficulty!r}")

        score = candidate.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not (0 <= score <= 100):
            fail(f"{name}: score must be an integer from 0 to 100")

        evidence_urls = candidate.get("evidence_urls")
        if not isinstance(evidence_urls, list) or not evidence_urls:
            fail(f"{name}: evidence_urls must contain at least one URL")
        if not all(valid_http_url(url) for url in evidence_urls):
            fail(f"{name}: evidence_urls contains an invalid URL")

        pending_checks = candidate.get("pending_checks")
        if not isinstance(pending_checks, list) or not all(
            isinstance(item, str) for item in pending_checks
        ):
            fail(f"{name}: pending_checks must be a string array")

        if status == "RECOMMENDED" and pending_checks:
            fail(f"{name}: RECOMMENDED must not have pending_checks")

    checked_sources = data.get("checked_sources")
    if not isinstance(checked_sources, list) or not checked_sources:
        fail("checked_sources must be a non-empty array")

    saw_pub_dev = False
    saw_required = False
    required_incomplete = False

    for source in checked_sources:
        if not isinstance(source, dict):
            fail("each checked_sources item must be an object")

        name = source.get("name")
        url = source.get("url")
        required = source.get("required")
        result = source.get("result")

        if not isinstance(name, str) or not name.strip():
            fail("checked source has invalid name")
        if not valid_http_url(url):
            fail(f"checked source {name!r} has invalid URL")
        if not isinstance(required, bool):
            fail(f"checked source {name!r}: required must be boolean")
        if result not in ALLOWED_SOURCE_RESULTS:
            fail(f"checked source {name!r}: invalid result {result!r}")

        if "pub.dev" in urlparse(url).netloc.lower() or "pub.dev" in name.lower():
            saw_pub_dev = True
        if required:
            saw_required = True
            if result != "checked":
                required_incomplete = True

    if not saw_pub_dev:
        fail("checked_sources must include pub.dev")
    if not saw_required:
        fail("checked_sources must include at least one required dedup source")

    if required_incomplete:
        recommended = [c["name"] for c in candidates if c["status"] == "RECOMMENDED"]
        if recommended:
            fail(
                "required source is incomplete, so no candidate may be RECOMMENDED; "
                f"found {recommended}"
            )

    print(
        f"LIVE E2E PASSED: validated {len(candidates)} Flutter candidates and "
        f"{len(checked_sources)} checked sources"
    )


if __name__ == "__main__":
    main()
