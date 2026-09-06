from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative: str) -> ModuleType:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module(
    "check_article_static",
    "scripts/article/check_article_static.py",
)
frameworks, framework_families = checker.load_framework_config(ROOT / "resources/frameworks.yaml")


def article_body(*, title: str = "# Flutter 三方库鸿蒙适配实战", prompt_count: int = 2) -> str:
    prompt = "欢迎加入CPF-Flutter 鸿蒙社区：【https://atomgit.com/CPF-Flutter】"
    opening = prompt + "\n\n" if prompt_count >= 1 else ""
    ending = "\n\n" + prompt if prompt_count >= 2 else ""
    return title + "\n\n" + opening + ("适" * 820) + ending


def run(markdown: str, framework: str = "flutter") -> dict:
    return checker.check_article_static(
        markdown,
        framework,
        frameworks,
        framework_families,
    )


def test_valid_flutter_article_static_checks_pass() -> None:
    result = run(article_body())
    assert result["static_status"] == "PASS"
    assert result["blocking_checks"] == []
    assert result["checks"]["title-framework-explicit"]["status"] == "PASS"
    assert result["checks"]["minimum-chinese-characters"]["value"] >= 800
    assert result["checks"]["community-invitation-opening"]["status"] == "PASS"
    assert result["checks"]["community-invitation-ending"]["status"] == "PASS"


def test_fenced_code_does_not_count_toward_chinese_minimum() -> None:
    prompt = "欢迎加入CPF-Flutter 鸿蒙社区：【https://atomgit.com/CPF-Flutter】"
    markdown = (
        "# Flutter 三方库鸿蒙适配实战\n\n"
        + prompt
        + "\n\n"
        + ("文" * 100)
        + "\n```text\n"
        + ("码" * 1000)
        + "\n```\n"
        + prompt
    )
    result = run(markdown)
    assert result["static_status"] == "BLOCKED"
    assert result["checks"]["minimum-chinese-characters"]["status"] == "FAIL"
    assert result["checks"]["minimum-chinese-characters"]["value"] < 800


def test_gitcode_term_or_domain_blocks() -> None:
    result = run(article_body() + "\n历史链接：https://gitcode.com/example/repo")
    assert result["static_status"] == "BLOCKED"
    assert result["checks"]["gitcode-forbidden"]["status"] == "FAIL"
    assert "gitcode-forbidden" in result["blocking_checks"]


def test_title_must_name_framework() -> None:
    result = run(article_body(title="# 某三方库鸿蒙适配实战"))
    assert result["checks"]["title-framework-explicit"]["status"] == "FAIL"
    assert "title-framework-explicit" in result["blocking_checks"]


def test_opening_and_ending_need_two_prompt_occurrences() -> None:
    result = run(article_body(prompt_count=1))
    assert result["checks"]["community-invitation-opening"]["status"] == "PASS"
    assert result["checks"]["community-invitation-ending"]["status"] == "FAIL"


def test_applicationtpc_family_is_ambiguous() -> None:
    try:
        run("# ApplicationTPC 鸿蒙适配\n" + ("适" * 900), "applicationtpc")
    except ValueError as exc:
        assert "ambiguous framework family" in str(exc)
    else:
        raise AssertionError("generic ApplicationTPC must select arkts or cpp")


def main() -> None:
    test_valid_flutter_article_static_checks_pass()
    test_fenced_code_does_not_count_toward_chinese_minimum()
    test_gitcode_term_or_domain_blocks()
    test_title_must_name_framework()
    test_opening_and_ending_need_two_prompt_occurrences()
    test_applicationtpc_family_is_ambiguous()
    print("ARTICLE STATIC CHECK TESTS PASSED: deterministic text rules are stable")


if __name__ == "__main__":
    main()
