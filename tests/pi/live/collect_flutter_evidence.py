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


def http_bytes(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        body = response.read()
        headers = {key.lower(): value for key, value in response.headers.items()}
        if headers.get("content-encoding", "").lower() == "gzip":
            body = gzip.decompress(body)
        return body, headers


def http_json(url: str) -> Any:
    body, _ = http_bytes(url)
    return json.loads(body.decode("utf-8"))


def http_text(url: str) -> str:
    body, _ = http_bytes(url)
    return body.decode("utf-8", errors="replace")


def read_flutter_sources(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract Flutter discovery/dedup source lists without adding a YAML dependency."""
    discovery: list[dict[str, Any]] = []
    dedup: list[dict[str, Any]] = []
    in_flutter = False
    section: str | None = None
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if current and current.get("name") and current.get("url"):
            if section == "discovery_sources":
                discovery.append(current)
            elif section == "dedup_sources":
                dedup.append(current)
        current = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "  flutter:":
            in_flutter = True
            continue
        if in_flutter and re.match(r"^  [A-Za-z0-9_-]+:$", line):
            flush()
            break
        if not in_flutter:
            continue

        match = re.match(r"^    (discovery_sources|dedup_sources):$", line)
        if match:
            flush()
            section = match.group(1)
            continue

        if section not in {"discovery_sources", "dedup_sources"}:
            continue

        match = re.match(r"^      - name:\s*(.+?)\s*$", line)
        if match:
            flush()
            current = {"name": match.group(1).strip(), "required": False}
            continue
        if current is None:
            continue

        match = re.match(r"^        url:\s*(.+?)\s*$", line)
        if match:
            current["url"] = match.group(1).strip()
            continue
        match = re.match(r"^        required:\s*(true|false)\s*$", line, re.I)
        if match:
            current["required"] = match.group(1).lower() == "true"

    flush()
    if not discovery or not dedup:
        raise RuntimeError("Flutter discovery/dedup sources are missing from resources/frameworks.yaml")
    return discovery, dedup


def fetch_score(name: str) -> dict[str, Any] | None:
    url = f"https://pub.dev/api/packages/{urllib.parse.quote(name)}/score"
    try:
        data = http_json(url)
    except Exception:  # noqa: BLE001 - individual package failures are non-fatal.
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


def collect_pub_candidates(pub_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    completion_url = urllib.parse.urljoin(
        pub_url.rstrip("/") + "/", "api/package-name-completion-data"
    )
    try:
        payload = http_json(completion_url)
        names = payload.get("packages", []) if isinstance(payload, dict) else []
        names = [name for name in names if isinstance(name, str)]
    except Exception as exc:  # noqa: BLE001
        return [], {
            "name": "pub.dev",
            "url": pub_url,
            "required": False,
            "result": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }

    keyword_names = [
        name for name in names if any(keyword in name.lower() for keyword in KEYWORDS)
    ][:80]

    scored: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for item in executor.map(fetch_score, keyword_names):
            if item:
                scored.append(item)

    def rank(item: dict[str, Any]) -> tuple[int, int]:
        downloads = item.get("download_count_30_days")
        likes = item.get("like_count")
        return (
            downloads if isinstance(downloads, int) else -1,
            likes if isinstance(likes, int) else -1,
        )

    scored = [
        item
        for item in scored
        if "sdk:flutter" in item.get("tags", [])
        and any(
            tag in item.get("tags", [])
            for tag in ("platform:android", "platform:ios")
        )
    ]
    scored.sort(key=rank, reverse=True)
    for item in scored:
        item["pub_dev_url"] = f"https://pub.dev/packages/{urllib.parse.quote(item['name'])}"

    return scored[:12], {
        "name": "pub.dev",
        "url": pub_url,
        "required": False,
        "result": "checked",
        "completion_url": completion_url,
        "keyword_match_count": len(keyword_names),
        "candidate_count": len(scored),
    }


def atomgit_org(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.lower() in {"atomgit.com", "www.atomgit.com"} and len(parts) == 1:
        return parts[0]
    return None


def collect_org_repos(source: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    org = atomgit_org(str(source["url"]))
    if not org:
        return {**source, "result": "unavailable", "error": "not an AtomGit organization URL"}, []

    repo_names: list[str] = []
    api_urls: list[str] = []
    try:
        for page in range(1, 6):
            api_url = (
                "https://api.atomgit.com/api/v5/orgs/"
                f"{urllib.parse.quote(org)}/repos?per_page=100&page={page}"
            )
            api_urls.append(api_url)
            payload = http_json(api_url)
            if isinstance(payload, dict):
                payload = next(
                    (
                        payload[key]
                        for key in ("data", "items", "repos")
                        if isinstance(payload.get(key), list)
                    ),
                    payload,
                )
            if not isinstance(payload, list):
                raise RuntimeError("unexpected AtomGit organization response shape")

            for item in payload:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("path")
                    if isinstance(name, str) and name.strip():
                        repo_names.append(name.strip())
            if len(payload) < 100:
                break
    except Exception as exc:  # noqa: BLE001
        return {
            **source,
            "result": "unavailable",
            "api_urls": api_urls,
            "error": f"{type(exc).__name__}: {exc}",
        }, repo_names

    return {
        **source,
        "result": "checked",
        "api_urls": api_urls,
        "repo_count": len(repo_names),
    }, repo_names


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: collect_flutter_evidence.py <output-json>")

    output = Path(sys.argv[1])
    discovery_sources, dedup_sources = read_flutter_sources(Path("resources/frameworks.yaml"))
    pub_source = next(
        (source for source in discovery_sources if "pub.dev" in str(source.get("url", ""))),
        None,
    )
    if not pub_source:
        raise RuntimeError("Flutter pub.dev source is missing")

    candidates, pub_status = collect_pub_candidates(str(pub_source["url"]))
    if not candidates:
        raise RuntimeError(f"No Flutter candidates collected from pub.dev: {pub_status}")

    checked_sources: list[dict[str, Any]] = [pub_status]
    repo_names_by_source: dict[str, list[str]] = {}
    page_text_by_source: dict[str, str] = {}

    for source in dedup_sources:
        source_name = str(source["name"])
        if atomgit_org(str(source["url"])):
            status, repo_names = collect_org_repos(source)
            checked_sources.append(status)
            repo_names_by_source[source_name] = repo_names
            continue

        try:
            text = http_text(str(source["url"]))
            checked_sources.append(
                {
                    **source,
                    "result": "partial",
                    "note": "public page fetched; positive text matches are usable, absence is not exhaustive",
                }
            )
            page_text_by_source[source_name] = text
        except Exception as exc:  # noqa: BLE001
            checked_sources.append(
                {
                    **source,
                    "result": "unavailable",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for candidate in candidates:
        name = str(candidate["name"])
        norm = normalize(name)
        matches: list[dict[str, str]] = []
        for source in dedup_sources:
            source_name = str(source["name"])
            for repo_name in repo_names_by_source.get(source_name, []):
                repo_norm = normalize(repo_name)
                if norm and (norm == repo_norm or norm in repo_norm or repo_norm in norm):
                    matches.append(
                        {"source": source_name, "match": repo_name, "kind": "repository_name"}
                    )
            page_text = page_text_by_source.get(source_name, "")
            if page_text and re.search(
                rf"(?i)(?<![a-z0-9_]){re.escape(name)}(?![a-z0-9_])", page_text
            ):
                matches.append(
                    {"source": source_name, "match": name, "kind": "document_text"}
                )
        candidate["dedup_matches"] = matches

    evidence = {
        "schema_version": 1,
        "framework": "flutter",
        "official_skill_checks": {
            "flutter-library-search": "not_run",
            "ohos-flutter-plugin-adaptation-necessity-check": "not_run",
        },
        "collection_policy": {
            "network_timeout_seconds": HTTP_TIMEOUT,
            "candidate_keywords": list(KEYWORDS),
            "candidate_limit": 12,
            "note": "Absence from partial/unavailable sources is not proof that no adaptation exists.",
        },
        "candidates": candidates,
        "checked_sources": checked_sources,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_summary = ", ".join(
        f"{source.get('name')}={source.get('result')}" for source in checked_sources
    )
    print(f"Collected {len(candidates)} candidates; sources: {source_summary}")


if __name__ == "__main__":
    main()
