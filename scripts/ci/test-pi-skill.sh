#!/usr/bin/env bash
set -euo pipefail

: "${AGNES_API_KEY:?AGNES_API_KEY is required}"
: "${AGNES_BASE_URL:?AGNES_BASE_URL is required}"
: "${PI_MODEL:?PI_MODEL is required}"

if [[ $# -ne 5 ]]; then
  echo "usage: test-pi-skill.sh <contract-name> <skill-name> <skill-path> <prompt-file> <assert-script>" >&2
  exit 2
fi

CONTRACT_NAME="$1"
SKILL_NAME="$2"
SKILL_PATH="$3"
PROMPT_FILE="$4"
ASSERT_SCRIPT="$5"
PI_CONTRACT_TIMEOUT_SECONDS="${PI_CONTRACT_TIMEOUT_SECONDS:-180}"

mkdir -p "$HOME/.pi/agent" .artifacts/pi

python3 - "$HOME/.pi/agent/models.json" <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
config = {
    "providers": {
        "agnes-cn": {
            "baseUrl": os.environ["AGNES_BASE_URL"],
            "api": "openai-completions",
            "apiKey": "$AGNES_API_KEY",
            "authHeader": True,
            "models": [
                {"id": "agnes-2.5-flash", "name": "Agnes 2.5 Flash"},
            ],
        }
    }
}
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

OUTPUT_FILE=".artifacts/pi/${CONTRACT_NAME}-${PI_MODEL}.md"
CASE_PROMPT="$(cat "$PROMPT_FILE")"
PROMPT="/skill:${SKILL_NAME} ${CASE_PROMPT}"

timeout "${PI_CONTRACT_TIMEOUT_SECONDS}s" \
  pi \
    --provider agnes-cn \
    --model "$PI_MODEL" \
    --no-session \
    --no-tools \
    --skill "$SKILL_PATH" \
    -p "$PROMPT" \
  | tee "$OUTPUT_FILE"

python3 "$ASSERT_SCRIPT" "$OUTPUT_FILE"
