#!/usr/bin/env bash
set -euo pipefail

: "${AGNES_API_KEY:?AGNES_API_KEY is required}"
: "${AGNES_BASE_URL:?AGNES_BASE_URL is required}"
: "${PI_MODEL:?PI_MODEL is required}"
: "${FLUTTER_CANDIDATE:?FLUTTER_CANDIDATE is required}"

vendor_dir=".vendor/CPF-Flutter-skills"
artifact_dir=".artifacts/pi-official-flutter"
mkdir -p "$HOME/.pi/agent" "$artifact_dir"

bash scripts/ci/fetch-cpf-flutter-skills.sh "$vendor_dir"

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

output_file="$artifact_dir/${FLUTTER_CANDIDATE}.md"

prompt="/skill:flutter-library-search 请对 Flutter 包 ${FLUTTER_CANDIDATE} 执行官方库搜索与鸿蒙支持状态检查。

要求：
- 严格按已加载的 CPF-Flutter 官方 flutter-library-search Skill 执行；
- 只做该 Skill 覆盖的搜索/判定，不开始实际移植；
- 当前事实必须通过可访问来源核查，不凭记忆断言；
- 单个外部来源失败时记录失败并继续，不要无限重试；
- 最终先给简短的人类可读结论；
- 回答末尾追加以下机器可读区块：

<!-- OFFICIAL_RESULT -->
\`\`\`json
{
  \"candidate\": \"${FLUTTER_CANDIDATE}\",
  \"skill\": \"flutter-library-search\",
  \"result\": \"adapted | not_found | no_adaptation_needed | inconclusive\",
  \"reason\": \"...\",
  \"evidence_urls\": [\"https://...\"],
  \"pending_checks\": [\"...\"]
}
\`\`\`

`result` 只能使用上述四个 token；如果证据不足或来源不可用，必须使用 `inconclusive`。"

set +e
timeout --signal=TERM --kill-after=15s 3m \
  pi \
    --provider agnes-cn \
    --model "$PI_MODEL" \
    --no-session \
    --skill "$vendor_dir/flutter-library-search/SKILL.md" \
    -p "$prompt" \
  | tee "$output_file"
pi_exit=${PIPESTATUS[0]}
set -e

printf '{"candidate":"%s","pi_exit":%s}\n' "$FLUTTER_CANDIDATE" "$pi_exit" \
  > "$artifact_dir/runner-status.json"

# This smoke run is observational: preserve official Skill output even if the
# provider or an external source times out. Hard assertions happen in the
# deterministic handoff contract, not here.
exit 0
