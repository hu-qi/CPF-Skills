from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


ALLOWED_CONFIRMATION_STATUSES = {
    "CONFIRMED",
    "REJECTED",
    "NOT_PROVIDED",
    "NOT_APPLICABLE",
}

MANUAL_RULE_IDS = {
    "version-latest-primary",
    "practical-instructive-factual",
    "original-content",
    "real-development-history",
    "ai-not-majority-author",
    "atomgit-brand",
}

STATIC_RULE_IDS = {
    "title-framework-explicit",
    "minimum-chinese-characters",
    "gitcode-forbidden",
    "community-invitation-opening",
    "community-invitation-ending",
}

VALIDATION_RULE_TO_CHECK = {
    "real-implementation": "implementation",
    "build-success": "build",
    "demo-or-scenario": "demo",
    "functional-tests": "tests",
    "physical-device-run": "device_run",
    "successful-device-screenshots": "screenshots",
}

EXTERNAL_METRIC_RULES = {
    "duplication-rate": "duplication_rate_percent",
    "csdn-quality-check": "csdn_quality_score",
}


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def require_fixture_flag(payload: dict[str, Any], name: str) -> bool:
    value = payload.get("fixture_only", False)
    if not isinstance(value, bool):
        raise ValueError(f"{name}.fixture_only must be a boolean when provided")
    return value


def load_rules(path: Path) -> dict[str, Any]:
    return require_dict(yaml.safe_load(path.read_text(encoding="utf-8")), "article rules")


def collect_rules(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    groups = [
        config["version_policy"]["rules"],
        config["technical_evidence"]["before_article_prep"],
        config["article_content"]["pre_publish"],
        config["ai_policy"],
        config["brand_and_links"],
        config["publication_checks"]["pre_publish"],
        config["post_publish_metrics"],
    ]
    result: dict[str, dict[str, Any]] = {}
    for group in groups:
        for raw in require_list(group, "rule group"):
            rule = require_dict(raw, "rule")
            rule_id = rule.get("id")
            if not isinstance(rule_id, str) or not rule_id:
                raise ValueError("rule.id must be a non-empty string")
            if rule_id in result:
                raise ValueError(f"duplicate rule id: {rule_id}")
            result[rule_id] = rule
    return result


def make_check(
    rule_id: str,
    status: str,
    reason: str,
    *,
    evidence: list[str] | None = None,
    value: Any = None,
    threshold: Any = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": rule_id,
        "status": status,
        "reason": reason,
        "evidence": evidence or [],
    }
    if value is not None:
        result["value"] = value
    if threshold is not None:
        result["threshold"] = threshold
    return result


def check_static_rule(rule_id: str, static_report: dict[str, Any]) -> dict[str, Any]:
    checks = require_dict(static_report.get("checks"), "static_report.checks")
    raw = require_dict(checks.get(rule_id), f"static_report.checks.{rule_id}")
    status = raw.get("status")
    if status not in {"PASS", "FAIL"}:
        raise ValueError(f"static rule {rule_id} must be PASS or FAIL")
    return make_check(
        rule_id,
        status,
        str(raw.get("reason") or ""),
        value=raw.get("value"),
        threshold=raw.get("threshold"),
    )


def check_validation_rule(
    rule_id: str,
    check_name: str,
    validation_gate: dict[str, Any],
) -> dict[str, Any]:
    checks = require_dict(validation_gate.get("checks"), "validation_gate.checks")
    raw = require_dict(checks.get(check_name), f"validation_gate.checks.{check_name}")
    status = raw.get("status")
    evidence = raw.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        raise ValueError(f"validation_gate.checks.{check_name}.evidence must be a string list")
    if status == "VERIFIED":
        return make_check(rule_id, "PASS", f"Validation Gate 已验证 {check_name}。", evidence=evidence)
    if status in {"FAILED", "NOT_RUN", "MISSING"}:
        return make_check(rule_id, "FAIL", f"Validation Gate 中 {check_name}={status}。", evidence=evidence)
    raise ValueError(f"unsupported validation status for {check_name}: {status!r}")


def compare_threshold(value: float, threshold: dict[str, Any]) -> bool:
    operator = threshold.get("operator")
    target = threshold.get("value")
    if not isinstance(target, (int, float)):
        raise ValueError("threshold.value must be numeric")
    if operator == "gte":
        return value >= target
    if operator == "lte":
        return value <= target
    raise ValueError(f"unsupported threshold operator: {operator!r}")


def check_external_rule(
    rule_id: str,
    metric_name: str,
    rule: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    metrics = require_dict(context.get("external_metrics", {}), "context.external_metrics")
    value = metrics.get(metric_name)
    threshold = require_dict(rule.get("threshold"), f"rules.{rule_id}.threshold")
    if value is None:
        return make_check(
            rule_id,
            "EXTERNAL_REQUIRED",
            f"缺少实际外部指标 {metric_name}。",
            threshold=threshold,
        )
    if not isinstance(value, (int, float)):
        raise ValueError(f"context.external_metrics.{metric_name} must be numeric or null")
    passed = compare_threshold(float(value), threshold)
    return make_check(
        rule_id,
        "PASS" if passed else "FAIL",
        f"外部指标 {metric_name}={value} {'满足' if passed else '不满足'}阈值。",
        value=value,
        threshold=threshold,
    )


def check_manual_rule(
    rule_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    confirmations = require_dict(context.get("confirmations", {}), "context.confirmations")
    raw = confirmations.get(rule_id)
    if raw is None:
        return make_check(rule_id, "MANUAL_REQUIRED", "缺少作者/人工确认或可审计证据。")
    item = require_dict(raw, f"context.confirmations.{rule_id}")
    status = item.get("status")
    if status not in ALLOWED_CONFIRMATION_STATUSES:
        raise ValueError(
            f"context.confirmations.{rule_id}.status must be one of "
            + ", ".join(sorted(ALLOWED_CONFIRMATION_STATUSES))
        )
    evidence = item.get("evidence", [])
    if not isinstance(evidence, list) or not all(isinstance(value, str) and value.strip() for value in evidence):
        raise ValueError(f"context.confirmations.{rule_id}.evidence must be a list of non-empty strings")
    reason = item.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError(f"context.confirmations.{rule_id}.reason must be a string")

    if status == "CONFIRMED":
        return make_check(rule_id, "PASS", reason or "已由作者/人工确认。", evidence=evidence)
    if status == "REJECTED":
        return make_check(rule_id, "FAIL", reason or "人工确认该规则未满足。", evidence=evidence)
    if status == "NOT_APPLICABLE":
        return make_check(rule_id, "NOT_APPLICABLE", reason or "当前场景不适用。", evidence=evidence)
    return make_check(rule_id, "MANUAL_REQUIRED", reason or "尚未提供人工确认。", evidence=evidence)


def check_post_publish(rule_id: str, rule: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    metrics = require_dict(context.get("external_metrics", {}), "context.external_metrics")
    value = metrics.get("readership")
    threshold = require_dict(rule.get("threshold"), f"rules.{rule_id}.threshold")
    achieved = False
    if value is not None:
        if not isinstance(value, (int, float)):
            raise ValueError("context.external_metrics.readership must be numeric or null")
        achieved = compare_threshold(float(value), threshold)
    return make_check(
        rule_id,
        "POST_PUBLISH",
        "阅读量属于发布后指标，不阻塞发布前合规。" + ("当前已达到目标。" if achieved else "当前尚未确认达到目标。"),
        value=value,
        threshold=threshold,
    )


def build_report(
    static_report: dict[str, Any],
    validation_gate: dict[str, Any],
    context: dict[str, Any],
    rules_config: dict[str, Any],
) -> dict[str, Any]:
    framework = static_report.get("framework")
    if not isinstance(framework, str) or not framework:
        raise ValueError("static_report.framework must be a non-empty string")
    if validation_gate.get("framework") != framework:
        raise ValueError("static report and validation gate framework mismatch")

    validation_fixture_only = require_fixture_flag(validation_gate, "validation_gate")
    context_fixture_only = require_fixture_flag(context, "context")
    if validation_fixture_only != context_fixture_only:
        raise ValueError("validation gate and compliance context fixture_only flags must match")
    fixture_only = validation_fixture_only

    rules = collect_rules(rules_config)
    checks: list[dict[str, Any]] = []

    for rule_id in sorted(STATIC_RULE_IDS):
        checks.append(check_static_rule(rule_id, static_report))

    for rule_id, check_name in VALIDATION_RULE_TO_CHECK.items():
        checks.append(check_validation_rule(rule_id, check_name, validation_gate))

    for rule_id, metric_name in EXTERNAL_METRIC_RULES.items():
        checks.append(check_external_rule(rule_id, metric_name, rules[rule_id], context))

    for rule_id in sorted(MANUAL_RULE_IDS):
        checks.append(check_manual_rule(rule_id, context))

    checks.append(check_post_publish("readership", rules["readership"], context))

    checks.append(
        make_check(
            "version-harmony-fallback",
            "NOT_APPLICABLE",
            "兼容版本回退是例外规则；仅在实际发生回退时单独记录原因与环境。",
        )
    )
    checks.append(
        make_check(
            "recommended-ai-tool",
            "NOT_APPLICABLE",
            "CodeArts 为推荐项，不是发布前硬门禁；如活动要求推荐链接应使用当前活动提供链接。",
        )
    )

    blocking_rules = [item["id"] for item in checks if item["status"] in {"FAIL", "EXTERNAL_REQUIRED"}]
    manual_rules = [item["id"] for item in checks if item["status"] == "MANUAL_REQUIRED"]
    external_rules = [item["id"] for item in checks if item["status"] == "EXTERNAL_REQUIRED"]
    post_publish_rules = [item["id"] for item in checks if item["status"] == "POST_PUBLISH"]

    validation_ready = (
        validation_gate.get("phase") == "ARTICLE_PREP"
        and validation_gate.get("decision") == "PROCEED"
    )
    if not validation_ready and "validation-gate" not in blocking_rules:
        blocking_rules.insert(0, "validation-gate")

    if blocking_rules:
        status = "BLOCKED"
    elif manual_rules:
        status = "MANUAL_REVIEW_REQUIRED"
    else:
        status = "READY_TO_PUBLISH"

    publishable = status == "READY_TO_PUBLISH" and not fixture_only

    if fixture_only:
        next_actions = [
            "当前报告来自 fixture_only 测试数据，仅用于回归验证；不得作为真实文章发布资格或活动证据。"
        ]
    else:
        next_actions: list[str] = []
        if blocking_rules:
            next_actions.append("修复所有 FAIL，并补齐所有 EXTERNAL_REQUIRED 的真实外部结果。")
        if manual_rules:
            next_actions.append("完成 MANUAL_REQUIRED 项的作者/人工确认并保存证据。")
        if not next_actions:
            next_actions.append("发布前硬规则已完成；发布后继续跟踪 readership 指标。")

    return {
        "schema_version": 1,
        "fixture_only": fixture_only,
        "publishable": publishable,
        "framework": framework,
        "status": status,
        "blocking_rules": blocking_rules,
        "manual_rules": manual_rules,
        "external_rules": external_rules,
        "post_publish_rules": post_publish_rules,
        "checks": checks,
        "next_actions": next_actions,
    }


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: build_compliance_report.py <static-report-json> <validation-gate-json> "
            "<context-json> <article-rules-yaml> <report-json>"
        )

    static_path = Path(sys.argv[1])
    validation_path = Path(sys.argv[2])
    context_path = Path(sys.argv[3])
    rules_path = Path(sys.argv[4])
    output_path = Path(sys.argv[5])

    static_report = require_dict(json.loads(static_path.read_text(encoding="utf-8")), "static report")
    validation_gate = require_dict(json.loads(validation_path.read_text(encoding="utf-8")), "validation gate")
    context = require_dict(json.loads(context_path.read_text(encoding="utf-8")), "context")

    try:
        report = build_report(static_report, validation_gate, context, load_rules(rules_path))
    except ValueError as exc:
        raise SystemExit(f"cannot build article compliance report: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Article compliance: {report['framework']} -> {report['status']} "
        f"(blocking={len(report['blocking_rules'])}, manual={len(report['manual_rules'])}, "
        f"publishable={str(report['publishable']).lower()})"
    )


if __name__ == "__main__":
    main()
