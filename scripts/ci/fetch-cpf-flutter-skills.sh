#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.vendor/CPF-Flutter-skills}"
REPO_URL="https://atomgit.com/CPF-Flutter/skills.git"

rm -rf "$ROOT_DIR"
mkdir -p "$(dirname "$ROOT_DIR")"

# Bound external access so AtomGit availability cannot pin the CI runner.
timeout --signal=TERM --kill-after=10s 90s \
  git clone --depth 1 "$REPO_URL" "$ROOT_DIR"

required_skills=(
  "flutter-library-search"
  "ohos-flutter-plugin-adaptation-necessity-check"
)

for skill in "${required_skills[@]}"; do
  path="$ROOT_DIR/$skill/SKILL.md"
  if [[ ! -s "$path" ]]; then
    echo "::error::Required CPF-Flutter Skill missing: $path"
    exit 1
  fi
  echo "Found official Skill: $skill"
done

commit_sha="$(git -C "$ROOT_DIR" rev-parse HEAD)"
echo "CPF-Flutter skills commit: $commit_sha"

mkdir -p .artifacts/official-skills
cat > .artifacts/official-skills/cpf-flutter.json <<JSON
{
  "repository": "$REPO_URL",
  "commit": "$commit_sha",
  "skills": [
    "flutter-library-search",
    "ohos-flutter-plugin-adaptation-necessity-check"
  ]
}
JSON
