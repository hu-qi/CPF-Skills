from __future__ import annotations

import concurrent.futures
import gzip
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "CPF-Skills-CI/0.1 (+https://github.com/hu-qi/CPF-Skills)"
HTTP_TIMEOUT = 10
KEYWORDS = (
    "file",
    "video",
    "media",
    "audio",
    "image",
    "photo",
    "camera",
    "document",
    "pdf",
    "archive",
    "compress",
)


def request_bytes(url: str, timeout: int = HTTP_TIMEOUT) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
        if headers.get("content-encoding", "").lower() == "gzip":
            body = gzip.decompress(body)
        return body, headers


def request_json(url: str, timeout: int = HTTP_TIMEOUT) -> Any:
    body, _ = request_bytes(url, timeout=timeout)
    return json.loads(body.decode("utf-8"))


def fetch_with_status(url: str) -> dict[str, Any]:
    try:
        body, headers = request_bytes(url)
        return {
            "ok": True,
            "status": "checked",
            "content_type": headers.get("content-type", ""),
            "body": body.decode("utf-8", errors="replace"),
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": "unavailable",
            "body": "",
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:  # noqa: BLE001 - evidence collection must degrade, not crash.
        return {
            "ok": False,
            "status": "unavailable",
            "body": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_flutter_sources(config_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read just the source lists from frameworks.yaml without adding a YAML dependency."""
    lines = config_path.read_text(encoding="utf-8").splitlines()
    in_flutter = False
    section: str | None = None
    discovery: list[dict[str, Any]] = []
    dedup: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if current is None or "name" not in current or "url" not in current:
            current = None
            return
        if section == "discovery_sources":
            discovery.append(current)
        elif section == "dedup_sources":
            dedup.append(current)
        current = None

    for line in lines:
        if line == "  flutter:":
            in_flutter = True
            continue
        if in_flutter and re.match(r"^  [a-zA-Z0-9_-]+:$", line):
            flush()
            break
        if not in_flutter:
            continue

        section_match = re.match(r"^    (discovery_sources|dedup_sources):$", line)
        if section_match:
            flush()
            section = section_match.group(1)
            continue

        if section not in {"discovery_sources", "dedup_sources"}:
            continue

        name_match = re.match(r"^      - name:\s*(.+?)\s*$", line)
        if name_match:
            flush()
            current = {"name": name_match.group(1).strip(), "required": False}
            continue

        if current is None:
            continue

        url_match = re.match(r"^        url:\s*(.+?)\s*$", line)
        if url_match:
            current["url"] = url_match.group(1).strip()
            continue

        required_match = re.match(r"^        required:\s*(true|false)\s*$", line, re.I)
        if required_match:
            current["required"] = required_match.group(1).lower() == "true"

    flush()

    if not discovery:
        raise RuntimeError("Flutter discovery_sources not found in resources/frameworks.yaml")
    if not dedup:
        raise RuntimeError("Flutter dedup_sources not found in resources/frameworks.yaml")
    return discovery, dedup


def package_score(name: str) -> dict[str, Any] | None:
    url = f"https://pub.dev/api/packages/{urllib.parse.quote(name)}/score"
    try:
        data = request_json(url)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    return {
        "name": name,
        "like_count": data.get("likeCount"),
        "download_count_30_days": data.get("downloadCount30Days"),
        "granted_points": data.get("grantedPoints"),
        "max_points": data.get("maxPoints"),
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
    }


def discover_pub_candidates(pub_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    completion_url = urllib.parse.urljoin(pub_url.rstrip("/") + "/", "api/package-name-completion-data")
    try:
        data = request_json(completion_url)
        packages = data.get("packages", []) if isinstance(data, dict) else []
        packages = [item for item in packages if isinstance(item, str)]
    except Exception as exc:  # noqa: BLE001
        return [], {
            "name": "pub.dev",
            "url": pub_url,
            "required": False,
            "result": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }

    keyword_names = [
        name
        for name in packages
        if any(keyword in name.lower() for keyword in KEYWORDS)
    ][:80]

    scores: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(package_score, name): name for name in keyword_names}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                scores.append(result)

    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        downloads = item.get("download_count_30_days")
        likes = item.get("like_count")
        return (
            downloads if isinstance(downloads, int) else -1,
            likes if isinstance(likes, int) else -1,
        )

    flutter_scores = [
        item
        for item in scores
        if "sdk:flutter" in item.get("tags", [])
        and (
            "platform:android" in item.get("tags", [])
            or "platform:ios" in item.get("tags", [])
        )
    ]
    flutter_scores.sort(key=sort_key, reverse=True)

    return flutter_scores[:12], {
        "name": "pub.dev",
        "url": pub_url,
        "required": False,
        "result": "checked",
        "completion_url": completion_url,
        "matched_package_count": len(keyword_names),
        "scored_candidate_count": len(flutter_scores),
    }


def normalize_repo_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def atomgit_org_from_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {"atomgit.com", "www.atomgit.com"}:
        return None
    path = parsed.path.strip("/")
    if not path or "/" in path:
        return None
    return path


def collect_atomgit_org(source: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    org = atomgit_org_from_url(str(source["url"]))
    if not org:
        return {
            **source,
            "result": "unavailable",
            "error": "cannot derive AtomGit organization path from URL",
        }, []

    names: list[str] = []
    api_urls: list[str] = []
    try:
        for page in range(1, 6):
            api_url = (
                "https://api.atomgit.com/api/v5/orgs/"
                f"{urllib.parse.quote(org)}/repos?per_page=100&page={page}"
            )
            api_urls.append(api_url)
            data = request_json(api_url)
            if isinstance(data, dict):
                for key in ("data", "items", "repos"):
                    if isinstance(data.get(key), list):
                        data = data[key]
                        break
            if not isinstance(data, list):
                raise RuntimeError("unexpected AtomGit organization response shape")

            page_names = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("path")
                if isinstance(name, str) and name.strip():
                    page_names.append(name.strip())
            names.extend(page_names)
            if len(data) < 100:
                break
    except Exception as exc:  # noqa: BLE001
        return {
            **source,
            "result": "unavailable",
            "api_urls": api_urls,
            "error": f"{type(exc).__name__}: {exc}",
        }, names

    return {
        **source,
        "result": "checked",
        "api_urls": api_urls,
        "repo_count": len(names),
    }, names


def collect_dedup_source(source: dict[str, Any]) -> tuple[dict[str, Any], list[str], str]:
    org = atomgit_org_from_url(str(source["url"]))
    if org:
        status, names = collect_atomgit_org(source)
        return status, names, ""

    fetched = fetch_with_status(str(source["url"]))
    if not fetched["ok"]:
        return {
            **source,
            "result": "unavailable",
            "error": fetched["error"],
        }, [], ""

    # A rendered document page can support positive matches, but absence in the HTML
    # is not strong enough to prove a package is absent. Mark it partial conservatively.
    return {
        **source,
        "result": "partial",
        "note": "public page fetched; positive text matches are usable, absence is not exhaustive",
    }, [], fetched["body"]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: collect_flutter_evidence.py <output-json>")

    output_path = Path(sys.argv[1])
    discovery_sources, dedup_sources = load_flutter_sources(Path("resources/frameworks.yaml"))

    pub_source = next(
        (source for source in discovery_sources if "pub.dev" in str(source.get("url", ""))),
        None,
    )
    if pub_source is None:
        raise RuntimeError("Flutter pub.dev discovery source is missing")

    candidates, pub_status = discover_pub_candidates(str(pub_source["url"]))
    if not candidates:
        raise RuntimeError(f"No live Flutter candidates collected from pub.dev: {pub_status}")

    checked_sources: list[dict[str, Any]] = [pub_status]
    source_repo_names: dict[str, list[str]] = {}
    source_text: dict[str, str] = {}

    for source in dedup_sources:
        status, repo_names, text = collect_dedup_source(source)
        checked_sources.append(status)
        source_repo_names[str(source["name"])] = repo_names
        source_text[str(source["name"])] = text

    for candidate in candidates:
        name = str(candidate["name"])
        normalized = normalize_repo_name(name)
        dedup_matches: list[dict[str, str]] = []

        for source in dedup_sources:
            source_name = str(source["name"])
            for repo_name in source_repo_names.get(source_name, []):
                repo_norm = normalize_repo_name(repo_name)
                if normalized and (normalized == repo_norm or normalized in repo_norm or repo_norm in normalized):
                    dedup_matches.append(
                        {"source": source_name, "match": repo_name, "kind": "repository_name"}
                    )
            page_text = source_text.get(source_name, "")
            if page_text and re.search(rf"(?i)(?<![a-z0-9_]){re.escape(name)}(?![a-z0-9_])", page_text):
                dedup_matches.append(
                    {"source": source_name, "match": name, "kind": "document_text"}
                )

        candidate["pub_dev_url"] = f"https://pub.dev/packages/{urllib.parse.quote(name)}"
        candidate["dedup_matches"] = dedup_matches

    evidence = {
        "schema_version": 1,
        "framework": "flutter",
        "collection_policy": {
            "network_timeout_seconds": HTTP_TIMEOUT,
            "candidate_keywords": list(KEYWORDS),
            "candidate_limit": 12,
            "note": "Absence from a partial source is never treated as proof that no adaptation exists.",
        },
        "candidates": candidates,
        "checked_sources": checked_sources,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Collected {len(candidates)} candidates; "
        f"sources: {', '.join(f'{s.get('name')}={s.get('result')}' for s in checked_sources)}"
    )


if __name__ == "__main__":
    main()
