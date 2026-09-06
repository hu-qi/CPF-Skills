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

official_evidence_file="$artifact_dir/${FLUTTER_CANDIDATE}.official-evidence.json"
activity_evidence_file="$artifact_dir/${FLUTTER_CANDIDATE}.activity-evidence.json"
output_file="$artifact_dir/${FLUTTER_CANDIDATE}.md"
normalized_file="$artifact_dir/${FLUTTER_CANDIDATE}.handoff.json"
qualification_file="$artifact_dir/${FLUTTER_CANDIDATE}.qualification.json"
gate_file="$artifact_dir/${FLUTTER_CANDIDATE}.gate.json"
status_file="$artifact_dir/runner-status.json"

# Network-facing evidence collection is deterministic and independently bounded.
set +e
timeout --signal=TERM --kill-after=10s 90s \
  python3 tests/pi/live/collect_official_flutter_search_evidence.py \
    "$FLUTTER_CANDIDATE" "$official_evidence_file"
official_collector_exit=$?

timeout --signal=TERM --kill-after=10s 90s \
  python3 tests/pi/live/collect_flutter_candidate_activity_evidence.py \
    "$FLUTTER_CANDIDATE" "$activity_evidence_file"
activity_collector_exit=$?
set -e

if [[ "$official_collector_exit" -ne 0 || ! -s "$official_evidence_file" ]]; then
  : > "$output_file"
  python3 tests/pi/live/normalize_official_flutter_result.py \
    "$FLUTTER_CANDIDATE" 125 "$official_evidence_file" "$output_file" "$normalized_file"
  pi_exit=125
else
  evidence="$(cat "$official_evidence_file")"
  prompt="/skill:flutter-library-search 请严格依据已加载的 CPF-Flutter 官方 flutter-library-search Skill，对 Flutter 包 ${FLUTTER_CANDIDATE} 进行鸿蒙支持状态判断。

本次所有网络事实已经由确定性采集器提供。禁止再次联网或调用工具，只能使用下面的 LIVE_EVIDENCE_JSON。不要凭记忆补充事实。

如果证据足以对应官方 Skill 的三类业务结论，请映射为：
- 已适配 -> adapted
- 无需适配 -> no_adaptation_needed
- 需要适配 -> needs_adaptation

如果官方 Skill 要求的关键阶段因为来源 unavailable/partial 而无法可靠完成，使用 inconclusive，不要把“未发现”升级成确定结论。

先给一句简短结论，然后在末尾输出：

<!-- OFFICIAL_RESULT -->
\`\`\`json
{
  \"candidate\": \"${FLUTTER_CANDIDATE}\",
  \"skill\": \"flutter-library-search\",
  \"result\": \"adapted | needs_adaptation | no_adaptation_needed | inconclusive\",
  \"reason\": \"...\",
  \"evidence_urls\": [\"https://...\"],
  \"pending_checks\": [\"...\"]
}
\`\`\`

LIVE_EVIDENCE_JSON:
\`\`\`json
${evidence}
\`\`\`"

  set +e
  timeout --signal=TERM --kill-after=10s 75s \
    pi \
      --provider agnes-cn \
      --model "$PI_MODEL" \
      --no-session \
      --no-tools \
      --skill "$vendor_dir/flutter-library-search/SKILL.md" \
      -p "$prompt" \
    | tee "$output_file"
  pi_exit=${PIPESTATUS[0]}
  set -e

  python3 tests/pi/live/normalize_official_flutter_result.py \
    "$FLUTTER_CANDIDATE" "$pi_exit" "$official_evidence_file" "$output_file" "$normalized_file"
fi

qualification_built=false
gate_built=false
if [[ "$activity_collector_exit" -eq 0 && -s "$activity_evidence_file" && -s "$normalized_file" ]]; then
  python3 scripts/qualification/build_candidate_qualification.py \
    --framework flutter \
    --candidate "$FLUTTER_CANDIDATE" \
    --discovery-evidence "$activity_evidence_file" \
    --official-handoff "$normalized_file" \
    --output "$qualification_file"
  qualification_built=true

  python3 scripts/orchestrator/resolve_qualification_gate.py \
    "$qualification_file" "$gate_file"
  gate_built=true
fi

printf '{"candidate":"%s","official_collector_exit":%s,"activity_collector_exit":%s,"pi_exit":%s,"normalized":true,"qualification_built":%s,"gate_built":%s}\n' \
  "$FLUTTER_CANDIDATE" "$official_collector_exit" "$activity_collector_exit" "$pi_exit" "$qualification_built" "$gate_built" \
  > "$status_file"

# Observational smoke: artifacts preserve evidence, official judgment,
# normalized handoff, deterministic qualification, and orchestrator gate.
exit 0
