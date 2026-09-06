from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


def run(*args: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *(str(arg) for arg in args)],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def find_fixture_refs(value) -> list[str]:
    refs: list[str] = []
    if isinstance(value, str):
        if value.startswith("fixture://"):
            refs.append(value)
    elif isinstance(value, list):
        for item in value:
            refs.extend(find_fixture_refs(item))
    elif isinstance(value, dict):
        for item in value.values():
            refs.extend(find_fixture_refs(item))
    return refs


def test_initializer_creates_blocked_real_case_skeleton() -> None:
    with tempfile.TemporaryDirectory() as tmp_raw:
        case_dir = Path(tmp_raw) / "case"
        run("scripts/evidence/init_real_case.py", "arkts", "RealExampleLibrary", case_dir)

        qualification = load_json(case_dir / "qualification.json")
        validation = load_json(case_dir / "validation.json")
        notes = load_json(case_dir / "development-notes.json")
        context = load_json(case_dir / "compliance-context.json")

        for payload in (qualification, validation, notes, context):
            assert payload.get("fixture_only") is False
            assert find_fixture_refs(payload) == []

        assert qualification["framework"] == "arkts"
        assert qualification["candidate"] == "RealExampleLibrary"
        assert qualification["qualification"]["status"] == "NEEDS_OFFICIAL_CHECK"
        assert qualification["qualification"]["eligible_to_start_adaptation"] is False
        assert qualification["qualification"]["pending_checks"]

        for name, check in validation["validation"]["checks"].items():
            assert check["status"] == "MISSING", name
            assert check["evidence"] == [], name

        assert notes["problems"] == []
        assert notes["decisions"] == []
        assert notes["api_changes"] == []
        assert notes["source_refs"] == []

        assert context["external_metrics"]["duplication_rate_percent"] is None
        assert context["external_metrics"]["csdn_quality_score"] is None
        assert context["external_metrics"]["readership"] is None
        assert all(
            item["status"] == "NOT_PROVIDED"
            for item in context["confirmations"].values()
        )

        qualification_gate = case_dir / "qualification-gate.json"
        run(
            "scripts/orchestrator/resolve_qualification_gate.py",
            case_dir / "qualification.json",
            qualification_gate,
        )
        gate = load_json(qualification_gate)
        assert gate["phase"] == "QUALIFICATION"
        assert gate["decision"] == "BLOCKED"

        validation_gate = case_dir / "validation-gate.json"
        run(
            "scripts/orchestrator/resolve_validation_gate.py",
            case_dir / "validation.json",
            validation_gate,
        )
        vgate = load_json(validation_gate)
        assert vgate["phase"] == "VALIDATION"
        assert vgate["decision"] == "BLOCKED"
        assert len(vgate["pending_checks"]) == 6

        readme = (case_dir / "README.md").read_text(encoding="utf-8")
        assert "不是已通过案例" in readme
        assert "不得使用 `fixture://...`" in readme


def test_ambiguous_framework_family_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp_raw:
        result = run(
            "scripts/evidence/init_real_case.py",
            "applicationtpc",
            "ExampleLibrary",
            Path(tmp_raw) / "case",
            check=False,
        )
        assert result.returncode != 0
        assert "choose one of: arkts, cpp" in (result.stdout + result.stderr)


def test_nonempty_output_directory_is_not_overwritten() -> None:
    with tempfile.TemporaryDirectory() as tmp_raw:
        case_dir = Path(tmp_raw) / "case"
        case_dir.mkdir()
        (case_dir / "keep.txt").write_text("do not overwrite\n", encoding="utf-8")
        result = run(
            "scripts/evidence/init_real_case.py",
            "flutter",
            "ExamplePlugin",
            case_dir,
            check=False,
        )
        assert result.returncode != 0
        assert "output directory is not empty" in (result.stdout + result.stderr)
        assert (case_dir / "keep.txt").read_text(encoding="utf-8") == "do not overwrite\n"


def main() -> None:
    test_initializer_creates_blocked_real_case_skeleton()
    test_ambiguous_framework_family_is_rejected()
    test_nonempty_output_directory_is_not_overwritten()
    print("REAL CASE INTAKE TESTS PASSED: new cases start blocked and fixture-free")


if __name__ == "__main__":
    main()
