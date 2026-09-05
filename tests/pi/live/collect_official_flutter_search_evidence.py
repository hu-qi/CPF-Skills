from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "CPF-Skills-CI/0.2 (+https://github.com/hu-qi/CPF-Skills)"
HTTP_TIMEOUT = 8
MAX_DART_FILES = 24
CHANNEL_PATTERNS = (
    "MethodChannel",
    "EventChannel",
    "BasicMessageChannel",
    "PlatformInterface",
)
PLATFORM_PATTERNS = (
    "Platform.isAndroid",
    "Platform.isIOS",
    "defaultTargetPlatform",
    "TargetPlatform.android",
    "TargetPlatform.iOS",
)


def request_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def safe_json(url: str) -> tuple[str, Any | None, str | None]:
    try:
        return "checked", request_json(url), None
    except Exception as exc:  # noqa: BLE001 - source failures are evidence.
        return "unavailable", None, f"{type(exc).__name__}: {exc}"


def first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_github_repo(url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def pub_dev_evidence(candidate: str) -> dict[str, Any]:
    url = f"https://pub.dev/api/packages/{urllib.parse.quote(candidate)}"
    result, payload, error = safe_json(url)
    source: dict[str, Any] = {"name": "pub.dev", "url": url, "result": result}
    if error:
        source["error"] = error
        return {"source": source, "package": None}
    if not isinstance(payload, dict):
        source["result"] = "unavailable"
        source["error"] = "unexpected response shape"
        return {"source": source, "package": None}

    latest = payload.get("latest") if isinstance(payload.get("latest"), dict) else {}
    pubspec = latest.get("pubspec") if isinstance(latest.get("pubspec"), dict) else {}
    repository = first_string(pubspec.get("repository"), pubspec.get("homepage"))
    dependencies = pubspec.get("dependencies") if isinstance(pubspec.get("dependencies"), dict) else {}
    platforms = pubspec.get("platforms") if isinstance(pubspec.get("platforms"), dict) else {}
    plugin = None
    flutter_cfg = pubspec.get("flutter")
    if isinstance(flutter_cfg, dict):
        plugin_cfg = flutter_cfg.get("plugin")
        if isinstance(plugin_cfg, dict):
            plugin = plugin_cfg

    return {
        "source": source,
        "package": {
            "name": candidate,
            "version": pubspec.get("version"),
            "description": pubspec.get("description"),
            "repository": repository,
            "dependencies": sorted(str(key) for key in dependencies),
            "platforms": sorted(str(key) for key in platforms),
            "flutter_plugin": plugin,
        },
    }


def fetch_raw_dart(url: str) -> dict[str, Any]:
    try:
        text = request_text(url)
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "result": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
    channels = [pattern for pattern in CHANNEL_PATTERNS if pattern in text]
    platform_checks = [pattern for pattern in PLATFORM_PATTERNS if pattern in text]
    return {
        "url": url,
        "result": "checked",
        "channels": channels,
        "platform_checks": platform_checks,
    }


def github_source_evidence(repository_url: str | None) -> dict[str, Any]:
    parsed = parse_github_repo(repository_url)
    if not parsed:
        return {
            "source": {
                "name": "origin_repository",
                "url": repository_url,
                "result": "partial" if repository_url else "unavailable",
                "note": "deterministic source scan currently supports GitHub repositories",
            },
            "repository": None,
        }

    owner, repo = parsed
    repo_api = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
    result, metadata, error = safe_json(repo_api)
    source: dict[str, Any] = {"name": "origin_repository", "url": repo_api, "result": result}
    if error or not isinstance(metadata, dict):
        source["error"] = error or "unexpected repository response"
        return {"source": source, "repository": None}

    default_branch = metadata.get("default_branch") if isinstance(metadata.get("default_branch"), str) else "main"
    tree_url = f"{repo_api}/git/trees/{urllib.parse.quote(default_branch)}?recursive=1"
    tree_result, tree_payload, tree_error = safe_json(tree_url)
    if tree_result != "checked" or not isinstance(tree_payload, dict):
        source["result"] = "partial"
        source["tree_error"] = tree_error or "unexpected tree response"
        return {
            "source": source,
            "repository": {
                "owner": owner,
                "repo": repo,
                "default_branch": default_branch,
                "html_url": metadata.get("html_url"),
            },
        }

    tree = tree_payload.get("tree") if isinstance(tree_payload.get("tree"), list) else []
    paths = [item.get("path") for item in tree if isinstance(item, dict) and isinstance(item.get("path"), str)]
    top_dirs = sorted({path.split("/", 1)[0] for path in paths if "/" in path})
    ohos_paths = [path for path in paths if path == "ohos" or path.startswith("ohos/") or path == "harmony" or path.startswith("harmony/")]
    android_paths = [path for path in paths if path == "android" or path.startswith("android/")]
    ios_paths = [path for path in paths if path == "ios" or path.startswith("ios/")]
    dart_paths = [path for path in paths if path.startswith("lib/") and path.endswith(".dart")][:MAX_DART_FILES]

    raw_urls = [
        f"https://raw.githubusercontent.com/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/{urllib.parse.quote(default_branch)}/{path}"
        for path in dart_paths
    ]
    dart_scans: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for scan in executor.map(fetch_raw_dart, raw_urls):
            dart_scans.append(scan)

    channels = sorted({channel for scan in dart_scans for channel in scan.get("channels", [])})
    platform_checks = sorted({check for scan in dart_scans for check in scan.get("platform_checks", [])})
    unavailable_files = sum(1 for scan in dart_scans if scan.get("result") != "checked")
    if tree_payload.get("truncated") is True or unavailable_files:
        source["result"] = "partial"

    branches_url = f"{repo_api}/branches?per_page=100"
    branch_result, branch_payload, branch_error = safe_json(branches_url)
    harmony_branches: list[str] = []
    if branch_result == "checked" and isinstance(branch_payload, list):
        for item in branch_payload:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                name = item["name"]
                if any(token in name.lower() for token in ("ohos", "harmony", "openharmony")):
                    harmony_branches.append(name)
    else:
        source["result"] = "partial"
        source["branch_error"] = branch_error

    return {
        "source": source,
        "repository": {
            "owner": owner,
            "repo": repo,
            "default_branch": default_branch,
            "html_url": metadata.get("html_url"),
            "top_directories": top_dirs,
            "has_android": bool(android_paths),
            "has_ios": bool(ios_paths),
            "has_ohos_or_harmony": bool(ohos_paths),
            "harmony_branches": harmony_branches,
            "dart_files_scanned": len(dart_scans),
            "dart_files_unavailable": unavailable_files,
            "channel_markers": channels,
            "platform_check_markers": platform_checks,
        },
    }


def repository_search(name: str, url: str) -> dict[str, Any]:
    result, payload, error = safe_json(url)
    item: dict[str, Any] = {"name": name, "url": url, "result": result}
    if error:
        item["error"] = error
        return item
    matches: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_items = payload.get("items") if isinstance(payload.get("items"), list) else payload.get("data")
        if isinstance(raw_items, list):
            for raw in raw_items[:10]:
                if isinstance(raw, dict):
                    matches.append(
                        {
                            "name": raw.get("name") or raw.get("full_name"),
                            "full_name": raw.get("full_name"),
                            "html_url": raw.get("html_url") or raw.get("web_url"),
                        }
                    )
    elif isinstance(payload, list):
        for raw in payload[:10]:
            if isinstance(raw, dict):
                matches.append({"name": raw.get("name"), "full_name": raw.get("full_name"), "html_url": raw.get("html_url")})
    item["matches"] = matches
    return item


def cross_platform_search(candidate: str) -> list[dict[str, Any]]:
    q = urllib.parse.quote(candidate)
    queries = [
        ("gitcode_candidate_ohos", f"https://gitcode.com/api/v5/search/repos?q={q}%20ohos&per_page=10"),
        ("gitee_candidate_ohos", f"https://gitee.com/api/v5/search/repositories?q={q}%20ohos&per_page=10"),
        ("github_candidate_ohos", f"https://api.github.com/search/repositories?q={q}%20ohos&per_page=10"),
        ("github_candidate_harmony", f"https://api.github.com/search/repositories?q={q}%20harmony&per_page=10"),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(repository_search, name, url) for name, url in queries]
        return [future.result() for future in futures]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: collect_official_flutter_search_evidence.py <candidate> <output-json>")

    candidate = sys.argv[1].strip()
    output = Path(sys.argv[2])
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", candidate):
        raise SystemExit("candidate contains unsupported characters")

    pub = pub_dev_evidence(candidate)
    package = pub.get("package") if isinstance(pub, dict) else None
    repository_url = package.get("repository") if isinstance(package, dict) else None
    origin = github_source_evidence(repository_url if isinstance(repository_url, str) else None)
    searches = cross_platform_search(candidate)

    evidence = {
        "schema_version": 1,
        "candidate": candidate,
        "collector": {
            "mode": "official_flutter_library_search_evidence",
            "network_timeout_seconds": HTTP_TIMEOUT,
            "dart_file_limit": MAX_DART_FILES,
            "note": "Evidence collection is bounded and deterministic. Missing or unavailable sources must not be treated as proof of absence.",
        },
        "pub_dev": pub,
        "origin_repository": origin,
        "cross_platform_searches": searches,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_results = [pub.get("source", {}).get("result"), origin.get("source", {}).get("result")]
    source_results.extend(item.get("result") for item in searches)
    print(f"Collected official-search evidence for {candidate}: {source_results}")


if __name__ == "__main__":
    main()
