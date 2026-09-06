from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "e2e-fixture"


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def run_cli(*args: str | Path) -> None:
    subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def assert_fixture_inputs_are_not_real_evidence() -> None:
    qualification = load_json(FIXTURE / "qualification.json")
    validation = load_json(FIXTURE / "validation.json")
    notes = load_json(FIXTURE / "development-notes.json")
    context = load_json(FIXTURE / "compliance-context.json")

    for name, payload in {
        "qualification": qualification,
        "validation": validation,
        "development-notes": notes,
        "compliance-context": context,
    }.items():
        assert payload.get("fixture_only") is True, f"{name} must remain fixture_only"

    assert qualification.get("candidate") == "ExampleLibrary"

    validation_checks = validation["validation"]["checks"]
    for check in validation_checks.values():
        for ref in check.get("evidence", []):
            assert ref.startswith("fixture://")

    article = (FIXTURE / "article.md").read_text(encoding="utf-8")
    assert "不代表任何真实三方库适配经历" in article
    assert "不能作为征文、提交或真机验证证据" in article


def test_fixture_cli_chain() -> None:
    assert_fixture_inputs_are_not_real_evidence()

    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        validation_gate = tmp / "validation-gate.json"
        material_pack = tmp / "material-pack.json"
        static_report = tmp / "static-report.json"
        compliance_report = tmp / "compliance-report.json"

        run_cli(
            "scripts/orchestrator/resolve_validation_gate.py",
            FIXTURE / "validation.json",
            validation_gate,
        )
        gate = load_json(validation_gate)
        assert gate["phase"] == "ARTICLE_PREP"
        assert gate["decision"] == "PROCEED"
        assert gate["pending_checks"] == []

        run_cli(
            "scripts/article/build_article_material_pack.py",
            FIXTURE / "qualification.json",
            validation_gate,
            FIXTURE / "development-notes.json",
            material_pack,
        )
        pack = load_json(material_pack)
        assert pack["qualification_status"] == "RECOMMENDED"
        assert pack["validation_status"] == "ARTICLE_PREP/PROCEED"
        assert pack["material_gaps"] == []
        assert pack["ai_boundary"]["full_article_generation_allowed"] is False

        run_cli(
            "scripts/article/check_article_static.py",
            FIXTURE / "article.md",
            "arkts",
            "resources/frameworks.yaml",
            static_report,
        )
        static = load_json(static_report)
        assert static["static_status"] == "PASS"
        assert static["blocking_checks"] == []
        assert static["checks"]["minimum-chinese-characters"]["value"] >= 800

        run_cli(
            "scripts/article/build_compliance_report.py",
            static_report,
            validation_gate,
            FIXTURE / "compliance-context.json",
            "resources/article-rules.yaml",
            compliance_report,
        )
        compliance = load_json(compliance_report)
        assert compliance["status"] == "READY_TO_PUBLISH"
        assert compliance["blocking_rules"] == []
        assert compliance["manual_rules"] == []
        assert compliance["external_rules"] == []
        assert compliance["post_publish_rules"] == ["readership"]


def main() -> None:
    test_fixture_cli_chain()
    print("E2E ARTICLE FIXTURE PASSED: CLI chain works without treating fixture data as real evidence")


if __name__ == "__main__":
    main()
