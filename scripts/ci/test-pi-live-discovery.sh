#!/usr/bin/env bash
set -euo pipefail

: "${AGNES_API_KEY:?AGNES_API_KEY is required}"
: "${AGNES_BASE_URL:?AGNES_BASE_URL is required}"
: "${PI_MODEL:?PI_MODEL is required}"

mkdir -p "$HOME/.pi/agent" .artifacts/pi-live

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
                {"id": "agnes-2.5-pro", "name": "Agnes 2.5 Pro"},
            ],
        }
    }
}
path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

output_file=".artifacts/pi-live/flutter-discovery-${PI_MODEL}.md"
case_prompt="$(cat tests/pi/live/flutter-discovery.prompt.md)"
prompt="/skill:thirdparty-library-discovery ${case_prompt}"

# Bound the whole agent run so a slow external source cannot pin a CI runner.
# timeout exits with 124; the artifact upload step still preserves any partial output.
timeout --signal=TERM --kill-after=15s 5m \
  pi \
    --provider agnes-cn \
    --model "$PI_MODEL" \
    --no-session \
    --skill .atomcode/skills/thirdparty-library-discovery/SKILL.md \
    -p "$prompt" \
  | tee "$output_file"

python3 tests/pi/live/assert_flutter_discovery.py "$output_file"
