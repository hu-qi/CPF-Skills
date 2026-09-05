#!/usr/bin/env bash
set -euo pipefail

: "${AGNES_API_KEY:?AGNES_API_KEY is required}"
: "${AGNES_BASE_URL:?AGNES_BASE_URL is required}"
: "${PI_MODEL:?PI_MODEL is required}"

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

run_contract() {
  local name="$1"
  local prompt_file="$2"
  local assert_script="$3"
  local output_file=".artifacts/pi/${name}-${PI_MODEL}.md"
  local case_prompt
  case_prompt="$(cat "$prompt_file")"

  local prompt="/skill:thirdparty-library-discovery ${case_prompt}"

  pi \
    --provider agnes-cn \
    --model "$PI_MODEL" \
    --no-session \
    --skill .atomcode/skills/thirdparty-library-discovery/SKILL.md \
    -p "$prompt" \
    | tee "$output_file"

  python3 "$assert_script" "$output_file"
}

run_contract \
  "discovery-contract" \
  "tests/pi/discovery-contract.prompt.md" \
  "tests/pi/assert_discovery_contract.py"

run_contract \
  "official-handoff-contract" \
  "tests/pi/official-handoff-contract.prompt.md" \
  "tests/pi/assert_official_handoff_contract.py"
