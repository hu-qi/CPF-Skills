#!/usr/bin/env bash
set -euo pipefail

: "${AGNES_API_KEY:?AGNES_API_KEY is required}"
: "${AGNES_BASE_URL:?AGNES_BASE_URL is required}"
: "${PI_MODEL:?PI_MODEL is required}"

mkdir -p "$HOME/.pi/agent" .artifacts/pi

cat > "$HOME/.pi/agent/models.json" <<'JSON'
{
  "providers": {
    "agnes-cn": {
      "baseUrl": "https://api.agnes-ai.cn/v1",
      "api": "openai-completions",
      "apiKey": "$AGNES_API_KEY",
      "authHeader": true,
      "models": [
        {
          "id": "agnes-2.5-flash",
          "name": "Agnes 2.5 Flash"
        },
        {
          "id": "agnes-2.5-pro",
          "name": "Agnes 2.5 Pro"
        }
      ]
    }
  }
}
JSON

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
