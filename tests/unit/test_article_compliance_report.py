from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative: str) -> ModuleType:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregator = load_module(
    "build_compliance_report",
    "scripts/article/build_compliance_report.py",
)
rules = yaml.safe_load((ROOT / "resources/article-rules.yaml").read_text(encoding="utf-8"))


def static_report() -> dict:
    return {
        "framework": "flutter",
        "static_status": "PASS",
        "checks": {
            "title-framework-explicit": {"status": "PASS", "reason": "ok"},
            "minimum-chinese-characters": {"status": "PASS", "reason": "ok", "value": 900, "threshold": 800},
            "gitcode-forbidden": {"status": "PASS", "reason": "ok"},
            "community-invitation-opening": {"status": "PASS", "reason": "ok"},
            "community-invitation-ending": {"status": "PASS", "reason": "ok"},
        },
    }


def validation_gate(*, ready: bool = True) -> dict:
    status = "VERIFIED" if ready else "MISSING"
    checks = {}
    for name in ("implementation", "build", "demo", "tests", "device_run", "screenshots"):
        checks[name] = {
            "status": status,
            "evidence": [f"artifact://{name}"] if ready else [],
        }
    return {
        "framework": "flutter",
        "candidate": "ExamplePlugin",
        "phase": "ARTICLE_PREP" if ready else "VALIDATION",
        "decision": "PROCEED" if ready else "BLOCKED",
        "checks": checks,
    }


def confirmed_context(*, duplication: float | None = 20, csdn: float | None = 85, readership: float | None = None) -> dict:
    confirmations = {}
    for rule_id in aggregator.MANUAL_RULE_IDS:
        confirmations[rule_id] = {
            "status": "CONFIRMED",
            "evidence": [f"confirmation://{rule_id}"],
        }
    return {
        "external_metrics": {
            "duplication_rate_percent": duplication,
            "csdn_quality_score": csdn,
            "readership": readership,
        },
        "confirmations": confirmations,
    }


def build(static: dict | None = None, validation: dict | None = None, context: dict | None = None) -> dict:
    return aggregator.build_report(
        static or static_report(),
        validation or validation_gate(),
        context or confirmed_context(),
        rules,
    )


def check_by_id(report: dict, rule_id: str) -> dict:
    return next(item for item in report["checks"] if item["id"] == rule_id)


def test_fully_confirmed_pre_publish_rules_are_ready() -> None:
    report = build()
    assert report["status"] == "READY_TO_PUBLISH"
    assert report["blocking_rules"] == []
    assert report["manual_rules"] == []
    assert report["external_rules"] == []
    assert report["post_publish_rules"] == ["readership"]
    assert check_by_id(report, "readership")["status"] == "POST_PUBLISH"


def test_missing_external_metrics_block() -> None:
    report = build(context=confirmed_context(duplication=None, csdn=None))
    assert report["status"] == "BLOCKED"
    assert set(report["external_rules"]) == {"duplication-rate", "csdn-quality-check"}
    assert "duplication-rate" in report["blocking_rules"]
    assert "csdn-quality-check" in report["blocking_rules"]


def test_manual_confirmations_do_not_get_auto_passed() -> None:
    context = confirmed_context()
    context["confirmations"].pop("original-content")
    report = build(context=context)
    assert report["status"] == "MANUAL_REVIEW_REQUIRED"
    assert "original-content" in report["manual_rules"]
    assert check_by_id(report, "original-content")["status"] == "MANUAL_REQUIRED"


def test_validation_gate_blocks_article_readiness() -> None:
    report = build(validation=validation_gate(ready=False))
    assert report["status"] == "BLOCKED"
    assert "validation-gate" in report["blocking_rules"]
    for rule_id in aggregator.VALIDATION_RULE_TO_CHECK:
        assert check_by_id(report, rule_id)["status"] == "FAIL"


def test_failed_static_rule_blocks() -> None:
    static = static_report()
    static["checks"]["gitcode-forbidden"] = {
        "status": "FAIL",
        "reason": "found GitCode",
    }
    static["static_status"] = "BLOCKED"
    report = build(static=static)
    assert report["status"] == "BLOCKED"
    assert "gitcode-forbidden" in report["blocking_rules"]


def test_low_readership_never_blocks_pre_publish() -> None:
    report = build(context=confirmed_context(readership=10))
    assert report["status"] == "READY_TO_PUBLISH"
    readership = check_by_id(report, "readership")
    assert readership["status"] == "POST_PUBLISH"
    assert "尚未确认达到目标" in readership["reason"]
    assert "readership" not in report["blocking_rules"]


def main() -> None:
    test_fully_confirmed_pre_publish_rules_are_ready()
    test_missing_external_metrics_block()
    test_manual_confirmations_do_not_get_auto_passed()
    test_validation_gate_blocks_article_readiness()
    test_failed_static_rule_blocks()
    test_low_readership_never_blocks_pre_publish()
    print("ARTICLE COMPLIANCE TESTS PASSED: full pre-publish status is deterministic")


if __name__ == "__main__":
    main()
