from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_DIR = ROOT / "scripts" / "orchestrator"
ARTICLE_DIR = ROOT / "scripts" / "article"
for directory in (ORCHESTRATOR_DIR, ARTICLE_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from build_compliance_report import MANUAL_RULE_IDS  # noqa: E402
from resolve_framework_route import load_framework_config, resolve_framework_key  # noqa: E402


VALIDATION_CHECKS = (
    "implementation",
    "build",
    "demo",
    "tests",
    "device_run",
    "screenshots",
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_case(framework: str, candidate: str) -> dict[str, dict[str, Any]]:
    candidate = candidate.strip()
    if not candidate:
        raise ValueError("candidate must be a non-empty string")

    frameworks, families = load_framework_config(ROOT / "resources" / "frameworks.yaml")
    key = resolve_framework_key(framework, frameworks, families)

    qualification = {
        "schema_version": 1,
        "fixture_only": False,
        "framework": key,
        "candidate": candidate,
        "qualification": {
            "status": "NEEDS_OFFICIAL_CHECK",
            "eligible_to_start_adaptation": False,
            "pending_checks": [
                "完成真实候选资格、官方技术判断与活动 required 去重后，替换本模板 qualification。"
            ],
            "reason": "real-case intake 初始化：尚未提供真实资格证据。",
        },
        "evidence": [],
    }

    checks: dict[str, dict[str, Any]] = {}
    for name in VALIDATION_CHECKS:
        checks[name] = {
            "status": "MISSING",
            "evidence": [],
        }
    checks["device_run"]["details"] = {
        "device_kind": None,
        "platform": None,
        "device_model": None,
    }

    validation = {
        "schema_version": 1,
        "fixture_only": False,
        "framework": key,
        "candidate": candidate,
        "validation": {
            "checks": checks,
        },
    }

    development_notes = {
        "schema_version": 1,
        "fixture_only": False,
        "summary": "",
        "problems": [],
        "decisions": [],
        "api_changes": [],
        "source_refs": [],
    }

    confirmations = {
        rule_id: {
            "status": "NOT_PROVIDED",
            "evidence": [],
            "reason": "尚未提供真实作者/人工确认。",
        }
        for rule_id in sorted(MANUAL_RULE_IDS)
    }
    compliance_context = {
        "schema_version": 1,
        "fixture_only": False,
        "external_metrics": {
            "duplication_rate_percent": None,
            "csdn_quality_score": None,
            "readership": None,
        },
        "confirmations": confirmations,
    }

    return {
        "qualification.json": qualification,
        "validation.json": validation,
        "development-notes.json": development_notes,
        "compliance-context.json": compliance_context,
    }


def render_case_readme(framework: str, candidate: str) -> str:
    return f"""# Real Case Intake: {candidate}\n\nFramework: `{framework}`\n\n本目录由 `scripts/evidence/init_real_case.py` 初始化。它是**真实案例采集工作区**，不是已通过案例。初始化后所有门禁默认阻塞。\n\n## 1. 先完成资格\n\n`qualification.json` 初始为：\n\n```text\nstatus = NEEDS_OFFICIAL_CHECK\neligible_to_start_adaptation = false\n```\n\n用真实 discovery、官方 Skill 结论和活动 required 去重结果替换它。不要手工把状态改成 `RECOMMENDED` 来绕过证据。\n\n验证：\n\n```bash\npython3 scripts/orchestrator/resolve_qualification_gate.py \\\n  <case-dir>/qualification.json \\\n  <case-dir>/qualification-gate.json\n```\n\n只有得到 `ADAPTATION/PROCEED` 才进入实际适配。\n\n## 2. 收集真实 Validation evidence\n\n`validation.json` 的六项初始都是 `MISSING`：\n\n```text\nimplementation\nbuild\ndemo\ntests\ndevice_run\nscreenshots\n```\n\n逐项替换为真实结果。`VERIFIED` 必须附可审计 evidence；`device_run=VERIFIED` 还必须是 HarmonyOS/OpenHarmony 实体设备。\n\n```bash\npython3 scripts/orchestrator/resolve_validation_gate.py \\\n  <case-dir>/validation.json \\\n  <case-dir>/validation-gate.json\n```\n\n只有得到 `ARTICLE_PREP/PROCEED` 才能准备文章。\n\n## 3. 记录真实开发过程\n\n在 `development-notes.json` 填写真实的：\n\n- `problems`：实际遇到的问题/失败尝试；\n- `decisions`：真实技术取舍；\n- `api_changes`：真实接口/行为变化；\n- `source_refs`：commit、diff、日志、issue、测试结果等引用。\n\n没有发生的内容保持为空，不要为了文章完整性虚构。\n\n## 4. 外部与人工合规\n\n`compliance-context.json` 初始不提供任何通过结论：\n\n- 重复率：`null`；\n- CSDN 质量分：`null`；\n- readership：`null`；\n- 所有人工确认：`NOT_PROVIDED`。\n\n只有拿到真实外部结果或真实作者确认后再填入。\n\n## Evidence 红线\n\n本目录必须保持：\n\n```text\nfixture_only = false\n```\n\n不得使用 `fixture://...`。真实 Material Pack / Compliance 会拒绝测试证据引用。\n"""


def initialize_case(framework: str, candidate: str, output_dir: Path) -> str:
    payloads = build_case(framework, candidate)
    canonical_framework = str(payloads["qualification.json"]["framework"])

    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, payload in payloads.items():
        write_json(output_dir / filename, payload)
    (output_dir / "README.md").write_text(
        render_case_readme(canonical_framework, candidate.strip()),
        encoding="utf-8",
    )
    return canonical_framework


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: init_real_case.py <framework> <candidate> <output-dir>"
        )

    framework = sys.argv[1]
    candidate = sys.argv[2]
    output_dir = Path(sys.argv[3])

    try:
        canonical = initialize_case(framework, candidate, output_dir)
    except ValueError as exc:
        raise SystemExit(f"cannot initialize real case: {exc}") from exc

    print(
        f"Real case intake initialized: framework={canonical}, "
        f"candidate={candidate.strip()}, dir={output_dir}"
    )


if __name__ == "__main__":
    main()
