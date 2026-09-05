from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "CPF-Skills-CI/0.3 (+https://github.com/hu-qi/CPF-Skills)"
HTTP_TIMEOUT = 8
GIT_TIMEOUT = 35
MAX_DART_FILES = 64
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


def run_command(args: list[str], *, cwd: Path | None = None, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def git_remote_branches(repository_url: str) -> tuple[list[str], str | None]:
    try:
        proc = run_command(
            ["git", "ls-remote", "--heads", repository_url],
            timeout=12,
        )
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return [], proc.stderr.strip() or f"git ls-remote exited {proc.returncode}"

    branches: list[str] = []
    for line in proc.stdout.splitlines():
        if "refs/heads/" not in line:
            continue
        name = line.split("refs/heads/", 1)[1].strip()
        if name:
            branches.append(name)
    return branches, None


def pubspec_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"(?m)^name:\s*['\"]?([A-Za-z0-9_.-]+)['\"]?\s*(?:#.*)?$", text)
    return match.group(1) if match else None


def relative_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        try:
            paths.append(path.relative_to(root).as_posix())
        except ValueError:
            continue
    return paths


def scan_dart_files(package_root: Path) -> tuple[list[str], list[str], int, list[str]]:
    lib = package_root / "lib"
    if not lib.is_dir():
        return [], [], 0, []

    dart_files = sorted(lib.rglob("*.dart"))[:MAX_DART_FILES]
    channels: set[str] = set()
    platform_checks: set[str] = set()
    scanned_paths: list[str] = []
    for path in dart_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned_paths.append(path.relative_to(package_root).as_posix())
        channels.update(pattern for pattern in CHANNEL_PATTERNS if pattern in text)
        platform_checks.update(pattern for pattern in PLATFORM_PATTERNS if pattern in text)

    return sorted(channels), sorted(platform_checks), len(scanned_paths), scanned_paths


def git_source_evidence(candidate: str, repository_url: str | None) -> dict[str, Any]:
    if not repository_url or not repository_url.startswith(("https://", "http://")):
        return {
            "source": {
                "name": "origin_repository",
                "url": repository_url,
                "result": "unavailable",
                "error": "pub.dev did not expose a clonable http(s) repository URL",
            },
            "repository": None,
        }

    source: dict[str, Any] = {
        "name": "origin_repository",
        "url": repository_url,
        "result": "checked",
        "method": "git_clone_depth_1",
    }

    with tempfile.TemporaryDirectory(prefix="cpf-flutter-origin-") as tmp:
        repo_dir = Path(tmp) / "repo"
        try:
            proc = run_command(
                ["git", "clone", "--depth", "1", "--no-tags", repository_url, str(repo_dir)],
                timeout=GIT_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001
            source["result"] = "unavailable"
            source["error"] = f"{type(exc).__name__}: {exc}"
            return {"source": source, "repository": None}

        if proc.returncode != 0:
            source["result"] = "unavailable"
            source["error"] = proc.stderr.strip()[-800:] or f"git clone exited {proc.returncode}"
            return {"source": source, "repository": None}

        rev = run_command(["git", "rev-parse", "HEAD"], cwd=repo_dir, timeout=5)
        commit = rev.stdout.strip() if rev.returncode == 0 else None

        package_roots: list[Path] = []
        for pubspec in repo_dir.rglob("pubspec.yaml"):
            if ".git" in pubspec.parts:
                continue
            if pubspec_name(pubspec) == candidate:
                package_roots.append(pubspec.parent)

        if package_roots:
            package_root = sorted(package_roots, key=lambda path: len(path.parts))[0]
            package_root_match = True
        else:
            package_root = repo_dir
            package_root_match = False
            source["result"] = "partial"
            source["note"] = "cloned repository, but could not locate a pubspec.yaml whose name matches the candidate"

        paths = relative_paths(package_root)
        top_dirs = sorted({path.split("/", 1)[0] for path in paths if "/" in path})
        root_dirs = {path for path in paths if "/" not in path and (package_root / path).is_dir()}
        has_android = "android" in root_dirs
        has_ios = "ios" in root_dirs
        has_ohos_or_harmony = any(name in root_dirs for name in ("ohos", "harmony", "openharmony"))
        channels, platform_checks, dart_count, dart_paths = scan_dart_files(package_root)

        branches, branch_error = git_remote_branches(repository_url)
        harmony_branches = [
            name
            for name in branches
            if any(token in name.lower() for token in ("ohos", "harmony", "openharmony"))
        ]
        if branch_error:
            source["branch_check"] = "partial"
            source["branch_error"] = branch_error

        package_path = package_root.relative_to(repo_dir).as_posix()
        if package_path == ".":
            package_path = ""

        return {
            "source": source,
            "repository": {
                "html_url": repository_url,
                "commit": commit,
                "candidate_package_root_found": package_root_match,
                "candidate_package_path": package_path,
                "top_directories": top_dirs,
                "root_directories": sorted(root_dirs),
                "has_android": has_android,
                "has_ios": has_ios,
                "has_ohos_or_harmony": has_ohos_or_harmony,
                "harmony_branches": harmony_branches,
                "dart_files_scanned": dart_count,
                "dart_files": dart_paths,
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
    raw_items: Any = None
    if isinstance(payload, dict):
        raw_items = payload.get("items") if isinstance(payload.get("items"), list) else payload.get("data")
    elif isinstance(payload, list):
        raw_items = payload

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
    origin = git_source_evidence(
        candidate,
        repository_url if isinstance(repository_url, str) else None,
    )
    searches = cross_platform_search(candidate)

    evidence = {
        "schema_version": 2,
        "candidate": candidate,
        "collector": {
            "mode": "official_flutter_library_search_evidence",
            "network_timeout_seconds": HTTP_TIMEOUT,
            "git_timeout_seconds": GIT_TIMEOUT,
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
