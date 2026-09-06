#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.vendor/CPF-ApplicationTPC-skills}"
REPO_URL="https://atomgit.com/CPF-ApplicationTPC/skills.git"
ARTIFACT_DIR=".artifacts/official-skills/cpf-applicationtpc"

rm -rf "$ROOT_DIR"
mkdir -p "$(dirname "$ROOT_DIR")" "$ARTIFACT_DIR/snapshots"

timeout --signal=TERM --kill-after=10s 90s \
  git clone --depth 1 "$REPO_URL" "$ROOT_DIR"

commit_sha="$(git -C "$ROOT_DIR" rev-parse HEAD)"
echo "CPF-ApplicationTPC skills commit: $commit_sha"

mapfile -t skill_files < <(find "$ROOT_DIR" -type f -name SKILL.md -print | sort)
if [[ "${#skill_files[@]}" -eq 0 ]]; then
  echo "::error::No SKILL.md files found in CPF-ApplicationTPC official repository"
  exit 1
fi

python3 - "$ROOT_DIR" "$ARTIFACT_DIR/manifest.json" "$REPO_URL" "$commit_sha" <<'PY'
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
repo_url = sys.argv[3]
commit = sys.argv[4]
snapshot_root = manifest_path.parent / "snapshots"


def frontmatter(text: str) -> tuple[str | None, str | None]:
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end < 0:
        return None, None
    block = text[3:end]
    name = None
    description = None
    for line in block.splitlines():
        match = re.match(r"^name:\s*(.+?)\s*$", line)
        if match:
            name = match.group(1).strip().strip('"\'')
        match = re.match(r"^description:\s*(.+?)\s*$", line)
        if match:
            description = match.group(1).strip().strip('"\'')
    return name, description

skills = []
for path in sorted(root.rglob("SKILL.md")):
    relative = path.relative_to(root)
    text = path.read_text(encoding="utf-8", errors="replace")
    name, description = frontmatter(text)
    fallback_name = relative.parent.name
    skill_name = name or fallback_name
    shutil.copyfile(path, snapshot_root / f"{skill_name}.SKILL.md")
    skills.append(
        {
            "name": skill_name,
            "description": description,
            "path": relative.as_posix(),
        }
    )

manifest = {
    "schema_version": 1,
    "repository": repo_url,
    "commit": commit,
    "skill_count": len(skills),
    "skills": skills,
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

print(f"Found {len(skills)} CPF-ApplicationTPC official Skills")
for item in skills:
    print(f"- {item['name']}: {item['path']}")
PY
