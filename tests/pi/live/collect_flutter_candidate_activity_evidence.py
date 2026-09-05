from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from types import ModuleType
from typing import Any

GIT_TIMEOUT = 35


def load_discovery_module() -> ModuleType:
    path = Path(__file__).with_name("collect_flutter_evidence.py")
    spec = importlib.util.spec_from_file_location("collect_flutter_evidence_shared", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


discovery = load_discovery_module()


def atomgit_blob_spec(url: str) -> tuple[str, str, str, str] | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {"atomgit.com", "www.atomgit.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 5 or parts[2] != "blob":
        return None
    owner, repo, ref = parts[0], parts[1], parts[3]
    file_path = "/".join(parts[4:])
    if not all((owner, repo, ref, file_path)):
        return None
    return owner, repo, ref, file_path


def run(args: list[str], *, cwd: Path | None = None, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def collect_atomgit_blob(source: dict[str, Any]) -> tuple[dict[str, Any], str]:
    url = str(source.get("url", ""))
    spec = atomgit_blob_spec(url)
    if spec is None:
        return {**source, "result": "unavailable", "error": "not an AtomGit blob URL"}, ""

    owner, repo, ref, file_path = spec
    repo_url = f"https://atomgit.com/{owner}/{repo}.git"
    with tempfile.TemporaryDirectory(prefix="cpf-activity-doc-") as tmp:
        repo_dir = Path(tmp) / "repo"
        try:
            proc = run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    ref,
                    "--no-tags",
                    repo_url,
                    str(repo_dir),
                ],
                timeout=GIT_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                **source,
                "result": "unavailable",
                "repository": repo_url,
                "ref": ref,
                "path": file_path,
                "error": f"{type(exc).__name__}: {exc}",
            }, ""

        if proc.returncode != 0:
            return {
                **source,
                "result": "unavailable",
                "repository": repo_url,
                "ref": ref,
                "path": file_path,
                "error": proc.stderr.strip()[-800:] or f"git clone exited {proc.returncode}",
            }, ""

        target = repo_dir / file_path
        if not target.is_file():
            return {
                **source,
                "result": "unavailable",
                "repository": repo_url,
                "ref": ref,
                "path": file_path,
                "error": "file not found in cloned repository",
            }, ""

        text = target.read_text(encoding="utf-8", errors="replace")
        rev = run(["git", "rev-parse", "HEAD"], cwd=repo_dir, timeout=5)
        commit = rev.stdout.strip() if rev.returncode == 0 else None
        return {
            **source,
            "result": "checked",
            "repository": repo_url,
            "ref": ref,
            "path": file_path,
            "commit": commit,
            "collection_method": "git_clone_and_read_file",
        }, text


def collect_candidate(candidate: str) -> dict[str, Any]:
    _, dedup_sources = discovery.read_flutter_sources(Path("resources/frameworks.yaml"))
    profile = discovery.fetch_package_profile(candidate)
    candidate_evidence: dict[str, Any] = profile or {
        "name": candidate,
        "package_profile_result": "unavailable",
    }
    candidate_evidence["name"] = candidate

    checked_sources: list[dict[str, Any]] = []
    repo_names_by_source: dict[str, list[str]] = {}
    document_text_by_source: dict[str, str] = {}

    for source in dedup_sources:
        source_name = str(source.get("name"))
        url = str(source.get("url", ""))

        if discovery.atomgit_org(url):
            status, repo_names = discovery.collect_org_repos(source)
            checked_sources.append(status)
            repo_names_by_source[source_name] = repo_names
            continue

        if atomgit_blob_spec(url):
            status, text = collect_atomgit_blob(source)
            checked_sources.append(status)
            document_text_by_source[source_name] = text
            continue

        try:
            text = discovery.http_text(url)
            checked_sources.append(
                {
                    **source,
                    "result": "partial",
                    "note": "fallback web fetch; absence is not exhaustive",
                }
            )
            document_text_by_source[source_name] = text
        except Exception as exc:  # noqa: BLE001
            checked_sources.append(
                {
                    **source,
                    "result": "unavailable",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    matches: list[dict[str, str]] = []
    for source in dedup_sources:
        source_name = str(source.get("name"))
        for repo_name in repo_names_by_source.get(source_name, []):
            if discovery.repo_matches_package(candidate, repo_name):
                matches.append(
                    {
                        "source": source_name,
                        "match": repo_name,
                        "kind": "canonical_repository_name",
                    }
                )

        text = document_text_by_source.get(source_name, "")
        if text and re.search(
            rf"(?i)(?<![a-z0-9_]){re.escape(candidate)}(?![a-z0-9_])",
            text,
        ):
            matches.append(
                {
                    "source": source_name,
                    "match": candidate,
                    "kind": "document_text",
                }
            )

    candidate_evidence["dedup_matches"] = matches
    return {
        "schema_version": 1,
        "framework": "flutter",
        "candidate_scope": "single_candidate_activity_qualification",
        "candidates": [candidate_evidence],
        "checked_sources": checked_sources,
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: collect_flutter_candidate_activity_evidence.py <candidate> <output-json>"
        )

    candidate = sys.argv[1].strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", candidate):
        raise SystemExit("candidate contains unsupported characters")

    output = Path(sys.argv[2])
    evidence = collect_candidate(candidate)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = ", ".join(
        f"{item.get('name')}={item.get('result')}"
        for item in evidence.get("checked_sources", [])
        if isinstance(item, dict)
    )
    match_count = len(evidence["candidates"][0].get("dedup_matches", []))
    print(f"Collected activity evidence for {candidate}: {summary}; matches={match_count}")


if __name__ == "__main__":
    main()
