from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "resources/article-rules.yaml"


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must be an object")
    return value


def require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise AssertionError(f"{name} must be a list")
    return value


def load_rules() -> dict[str, Any]:
    return require_dict(yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")), "rules")


def rules_by_id(items: list[Any], name: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(items):
        item = require_dict(raw, f"{name}[{index}]")
        rule_id = item.get("id")
        assert isinstance(rule_id, str) and rule_id, f"{name}[{index}].id must be non-empty"
        assert rule_id not in result, f"duplicate rule id: {rule_id}"
        result[rule_id] = item
    return result


def threshold(rule: dict[str, Any]) -> tuple[str, int | float]:
    value = require_dict(rule.get("threshold"), f"{rule.get('id')}.threshold")
    operator = value.get("operator")
    number = value.get("value")
    assert isinstance(operator, str)
    assert isinstance(number, (int, float))
    return operator, number


def test_core_article_thresholds() -> None:
    rules = load_rules()
    content = rules_by_id(
        require_list(require_dict(rules["article_content"], "article_content")["pre_publish"], "article_content.pre_publish"),
        "article_content.pre_publish",
    )
    assert threshold(content["minimum-chinese-characters"]) == ("gte", 800)
    assert threshold(content["duplication-rate"]) == ("lte", 30)

    publication = rules_by_id(
        require_list(require_dict(rules["publication_checks"], "publication_checks")["pre_publish"], "publication_checks.pre_publish"),
        "publication_checks.pre_publish",
    )
    assert threshold(publication["csdn-quality-check"]) == ("gte", 80)
    assert publication["csdn-quality-check"]["url"] == "https://www.csdn.net/qc"

    post = rules_by_id(
        require_list(rules["post_publish_metrics"], "post_publish_metrics"),
        "post_publish_metrics",
    )
    assert threshold(post["readership"]) == ("gte", 1000)
    assert post["readership"]["severity"] == "post_publish"


def test_validation_rule_mapping_matches_gate_contract() -> None:
    rules = load_rules()
    technical = rules_by_id(
        require_list(require_dict(rules["technical_evidence"], "technical_evidence")["before_article_prep"], "technical_evidence.before_article_prep"),
        "technical_evidence.before_article_prep",
    )
    mapped = {item.get("validation_check") for item in technical.values()}
    assert mapped == {
        "implementation",
        "build",
        "demo",
        "tests",
        "device_run",
        "screenshots",
    }

    device = technical["physical-device-run"]
    assert device["device_kind"] == "physical"
    assert set(device["allowed_platforms"]) == {"HarmonyOS", "OpenHarmony"}


def test_brand_and_community_rules_are_explicit() -> None:
    rules = load_rules()
    brand = rules_by_id(
        require_list(rules["brand_and_links"], "brand_and_links"),
        "brand_and_links",
    )
    forbidden = brand["gitcode-forbidden"]
    assert "GitCode" in forbidden["forbidden_terms"]
    assert "gitcode.com" in forbidden["forbidden_domains"]
    assert "AtomGit" in brand["atomgit-brand"]["rule"]

    expected_template = "欢迎加入{community.name}：【{community.organization}】"
    assert brand["community-invitation-opening"]["template"] == expected_template
    assert brand["community-invitation-ending"]["template"] == expected_template


def test_ai_and_eligibility_rules_are_present() -> None:
    rules = load_rules()
    ai = rules_by_id(require_list(rules["ai_policy"], "ai_policy"), "ai_policy")
    assert ai["ai-not-majority-author"]["severity"] == "hard"
    assert "全部或大部分" in ai["ai-not-majority-author"]["rule"]

    eligibility = rules_by_id(
        require_list(require_dict(rules["eligibility"], "eligibility")["before_adaptation"], "eligibility.before_adaptation"),
        "eligibility.before_adaptation",
    )
    assert eligibility["library-not-already-adapted"]["severity"] == "hard"
    assert eligibility["adaptation-actually-needed"]["severity"] == "hard"
    assert eligibility["cross-platform-topic"]["severity"] == "hard"
    assert eligibility["environment-only-excluded"]["severity"] == "hard"


def test_rule_ids_are_globally_unique() -> None:
    rules = load_rules()
    groups = [
        rules["version_policy"]["rules"],
        rules["eligibility"]["before_adaptation"],
        rules["technical_evidence"]["before_article_prep"],
        rules["article_content"]["pre_publish"],
        rules["ai_policy"],
        rules["brand_and_links"],
        rules["publication_checks"]["pre_publish"],
        rules["post_publish_metrics"],
    ]
    seen: set[str] = set()
    for group in groups:
        for raw in require_list(group, "rule group"):
            item = require_dict(raw, "rule")
            rule_id = item.get("id")
            assert isinstance(rule_id, str) and rule_id
            assert rule_id not in seen, f"duplicate rule id: {rule_id}"
            seen.add(rule_id)


def main() -> None:
    test_core_article_thresholds()
    test_validation_rule_mapping_matches_gate_contract()
    test_brand_and_community_rules_are_explicit()
    test_ai_and_eligibility_rules_are_present()
    test_rule_ids_are_globally_unique()
    print("ARTICLE RULE TESTS PASSED: shared contest rules remain structurally stable")


if __name__ == "__main__":
    main()
