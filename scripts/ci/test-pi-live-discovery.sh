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

evidence_file=".artifacts/pi-live/flutter-evidence.json"
output_file=".artifacts/pi-live/flutter-discovery-${PI_MODEL}.md"

# Network collection is deterministic and independently bounded. The model never
# controls these requests, so a slow external site cannot create an unbounded tool loop.
timeout --signal=TERM --kill-after=10s 90s \
  python3 tests/pi/live/collect_flutter_evidence.py "$evidence_file"

case_prompt="$(cat tests/pi/live/flutter-discovery.prompt.md)"
evidence="$(cat "$evidence_file")"
prompt="/skill:thirdparty-library-discovery ${case_prompt}

LIVE_EVIDENCE_JSON:
\`\`\`json
${evidence}
\`\`\`"

# All live facts are already in the prompt. Disable tools to test only the Skill's
# decision logic over the auditable evidence snapshot.
timeout --signal=TERM --kill-after=10s 90s \
  pi \
    --provider agnes-cn \
    --model "$PI_MODEL" \
    --no-session \
    --no-tools \
    --skill .atomcode/skills/thirdparty-library-discovery/SKILL.md \
    -p "$prompt" \
  | tee "$output_file"

python3 tests/pi/live/assert_flutter_discovery.py "$output_file"
