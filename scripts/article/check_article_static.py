from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_DIR = ROOT / "scripts" / "orchestrator"
if str(ORCHESTRATOR_DIR) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_DIR))

from resolve_framework_route import load_framework_config, resolve_framework_key  # noqa: E402


FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
CHINESE_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^\)]+\)")
HTML_IMAGE_RE = re.compile(r"<img\b", re.IGNORECASE)


def require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def strip_code(markdown: str) -> str:
    without_fenced = FENCED_CODE_RE.sub("", markdown)
    return INLINE_CODE_RE.sub("", without_fenced)


def first_h1(markdown: str) -> str | None:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            return title or None
    return None


def framework_title_tokens(key: str, config: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    display_name = config.get("display_name")
    if isinstance(display_name, str) and display_name.strip():
        tokens.append(display_name.strip())
    aliases = config.get("aliases", [])
    if isinstance(aliases, list):
        tokens.extend(item.strip() for item in aliases if isinstance(item, str) and item.strip())

    if key == "react-native":
        tokens.append("RN")
    if key == "cpp":
        tokens.extend(["C++", "C/C++"])
    return sorted(set(tokens), key=lambda item: (-len(item), item.casefold()))


def check_title(title: str | None, tokens: list[str]) -> dict[str, Any]:
    if not title:
        return {
            "status": "FAIL",
            "reason": "文章缺少 Markdown H1 标题。",
            "matched_token": None,
        }
    folded = title.casefold()
    for token in tokens:
        if token.casefold() in folded:
            return {
                "status": "PASS",
                "reason": "标题明确包含框架/技术栈名称。",
                "matched_token": token,
            }
    return {
        "status": "FAIL",
        "reason": "标题未明确包含当前框架/技术栈名称。",
        "matched_token": None,
    }


def community_prompt(config: dict[str, Any]) -> str:
    community = require_dict(config.get("community"), "framework.community")
    name = community.get("name")
    organization = community.get("organization")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("framework.community.name must be a non-empty string")
    if not isinstance(organization, str) or not organization.strip():
        raise ValueError("framework.community.organization must be a non-empty string")
    return f"欢迎加入{name}：【{organization}】"


def check_community_prompt(markdown: str, prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    opening_window = markdown[:1500]
    ending_window = markdown[-1500:]
    occurrences = markdown.count(prompt)
    opening_ok = prompt in opening_window
    ending_ok = prompt in ending_window and occurrences >= 2
    return (
        {
            "status": "PASS" if opening_ok else "FAIL",
            "reason": "文章开头包含社区引导语。" if opening_ok else "文章开头缺少规范社区引导语。",
            "expected": prompt,
        },
        {
            "status": "PASS" if ending_ok else "FAIL",
            "reason": "文章结尾包含第二次社区引导语。" if ending_ok else "文章结尾缺少第二次规范社区引导语。",
            "expected": prompt,
            "total_occurrences": occurrences,
        },
    )


def check_article_static(
    markdown: str,
    framework: str,
    frameworks: dict[str, Any],
    framework_families: dict[str, Any],
) -> dict[str, Any]:
    key = resolve_framework_key(framework, frameworks, framework_families)
    config = require_dict(frameworks[key], f"frameworks.{key}")
    title = first_h1(markdown)
    non_code = strip_code(markdown)
    chinese_count = len(CHINESE_CHAR_RE.findall(non_code))

    title_result = check_title(title, framework_title_tokens(key, config))
    char_result = {
        "status": "PASS" if chinese_count >= 800 else "FAIL",
        "reason": "非代码中文正文达到 800 字要求。" if chinese_count >= 800 else "非代码中文正文不足 800 字。",
        "value": chinese_count,
        "threshold": 800,
    }

    forbidden_hits: list[str] = []
    lowered = markdown.casefold()
    if "gitcode" in lowered:
        forbidden_hits.append("GitCode")
    if "gitcode.com" in lowered and "gitcode.com" not in forbidden_hits:
        forbidden_hits.append("gitcode.com")
    forbidden_result = {
        "status": "FAIL" if forbidden_hits else "PASS",
        "reason": "发现活动禁止的 GitCode 品牌/链接。" if forbidden_hits else "未发现 GitCode 品牌/链接。",
        "hits": forbidden_hits,
    }

    prompt = community_prompt(config)
    opening_result, ending_result = check_community_prompt(markdown, prompt)

    has_image = bool(MARKDOWN_IMAGE_RE.search(markdown) or HTML_IMAGE_RE.search(markdown))
    image_result = {
        "status": "INFO",
        "reason": "检测到文章图片引用。" if has_image else "未检测到 Markdown/HTML 图片引用；真机截图是否有效仍以 Validation Artifact 为准。",
        "present": has_image,
    }

    checks = {
        "title-framework-explicit": title_result,
        "minimum-chinese-characters": char_result,
        "gitcode-forbidden": forbidden_result,
        "community-invitation-opening": opening_result,
        "community-invitation-ending": ending_result,
        "image-reference-present": image_result,
    }
    blocking = [
        check_id
        for check_id, result in checks.items()
        if result["status"] == "FAIL"
    ]

    return {
        "schema_version": 1,
        "framework": key,
        "title": title,
        "static_status": "PASS" if not blocking else "BLOCKED",
        "blocking_checks": blocking,
        "checks": checks,
        "note": "static_status 只覆盖可确定性检查的文章规则；原创性、重复率、AI 占比、CSDN 质量分和真机真实性仍需外部/人工证据。",
    }


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: check_article_static.py <article-md> <framework> <frameworks-yaml> <report-json>"
        )

    article_path = Path(sys.argv[1])
    framework = sys.argv[2]
    frameworks_path = Path(sys.argv[3])
    report_path = Path(sys.argv[4])

    markdown = article_path.read_text(encoding="utf-8")
    frameworks, framework_families = load_framework_config(frameworks_path)
    try:
        report = check_article_static(markdown, framework, frameworks, framework_families)
    except ValueError as exc:
        raise SystemExit(f"cannot check article: {exc}") from exc

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Article static check: {report['framework']} -> {report['static_status']} "
        f"({', '.join(report['blocking_checks']) or 'no blocking static checks'})"
    )


if __name__ == "__main__":
    main()
