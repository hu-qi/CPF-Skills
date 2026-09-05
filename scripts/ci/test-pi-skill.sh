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
            # Keep the key as an environment reference. Never materialize it in a repo file.
            "apiKey": "$AGNES_API_KEY",
            "authHeader": True,
            "models": [
                {"id": "agnes-2.5-flash", "name": "Agnes 2.5 Flash"},
                {"id": "agnes-2.5-pro", "name": "Agnes 2.5 Pro"},
            ],
        }
    }
}
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

output_file=".artifacts/pi/discovery-contract-${PI_MODEL}.md"
prompt="$(cat tests/pi/discovery-contract.prompt.md)"

pi \
  --provider agnes-cn \
  --model "$PI_MODEL" \
  --no-session \
  --skill .atomcode/skills/thirdparty-library-discovery/SKILL.md \
  -p "$prompt" \
  | tee "$output_file"

python3 tests/pi/assert_discovery_contract.py "$output_file"
