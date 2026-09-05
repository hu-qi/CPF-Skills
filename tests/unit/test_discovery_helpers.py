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


discovery = load_module("collect_flutter_evidence", "tests/pi/live/collect_flutter_evidence.py")
normalizer = load_module("normalize_official_flutter_result", "tests/pi/live/normalize_official_flutter_result.py")
official = load_module(
    "collect_official_flutter_search_evidence",
    "tests/pi/live/collect_official_flutter_search_evidence.py",
)
qualification = load_module(
    "build_candidate_qualification",
    "scripts/qualification/build_candidate_qualification.py",
)


def test_dedup_identity() -> None:
    assert discovery.repo_matches_package("file_picker", "fluttertpc_file_picker")
    assert discovery.repo_matches_package("archive", "fluttertpc_flutter_archive")
    assert discovery.repo_matches_package("audio_session", "flutter_audio_session")
    assert discovery.repo_matches_package("video_player", "ohos_flutter_video_player")

    # Regression: the old substring rule incorrectly treated these as the same package.
    assert not discovery.repo_matches_package("file", "file_picker")
    assert not discovery.repo_matches_package("image", "cached_network_image")
    assert not discovery.repo_matches_package("audio", "audio_session")


def checked_source() -> dict[str, str]:
    return {"result": "checked"}


def unavailable_search(name: str) -> dict[str, object]:
    return {"name": name, "result": "unavailable", "matches": []}


def test_result_specific_guardrails() -> None:
    base = {
        "pub_dev": {"source": checked_source()},
        "origin_repository": {
            "source": checked_source(),
            "repository": {
                "has_ohos_or_harmony": False,
                "harmony_branches": [],
            },
        },
        "cross_platform_searches": [
            unavailable_search("gitcode_candidate_ohos"),
            unavailable_search("gitee_candidate_ohos"),
            {"name": "github_candidate_ohos", "result": "checked", "matches": []},
        ],
    }

    # A source-structure conclusion does not require mirror searches to succeed.
    assert normalizer.critical_gaps(base, "no_adaptation_needed") == []

    # A negative adaptation search is an absence claim, so missing search sources matter.
    gaps = normalizer.critical_gaps(base, "needs_adaptation")
    assert "gitcode_candidate_ohos: unavailable" in gaps
    assert "gitee_candidate_ohos: unavailable" in gaps


def test_positive_adaptation_evidence() -> None:
    evidence = {
        "origin_repository": {
            "repository": {
                "has_ohos_or_harmony": False,
                "harmony_branches": [],
            }
        },
        "cross_platform_searches": [
            {
                "name": "github_candidate_ohos",
                "result": "checked",
                "matches": [{"full_name": "example/example_ohos"}],
            }
        ],
    }
    assert normalizer.positive_adaptation_evidence(evidence)


def test_pubspec_name_parser(tmp_path: Path) -> None:
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text("name: cached_network_image\nversion: 1.0.0\n", encoding="utf-8")
    assert official.pubspec_name(pubspec) == "cached_network_image"


def discovery_fixture(*, required_result: str = "checked", matches: list[dict[str, str]] | None = None) -> dict:
    return {
        "framework": "flutter",
        "candidates": [
            {
                "name": "ExamplePlugin",
                "repository": "https://example.invalid/ExamplePlugin",
                "dedup_matches": matches or [],
            }
        ],
        "checked_sources": [
            {
                "name": "CPF-Flutter",
                "url": "https://atomgit.com/CPF-Flutter",
                "required": True,
                "result": "checked",
            },
            {
                "name": "hxa-flutter",
                "url": "https://atomgit.com/hxa-flutter",
                "required": True,
                "result": required_result,
            },
        ],
    }


def handoff_fixture(*, library_result: str, necessity_result: str = "not_run") -> dict:
    return {
        "candidate": "ExamplePlugin",
        "official_checks": {
            "library_search": {
                "skill": "flutter-library-search",
                "result": library_result,
                "evidence": [],
                "reason": "fixture",
                "pending_checks": [],
            },
            "adaptation_necessity": {
                "skill": "ohos-flutter-plugin-adaptation-necessity-check",
                "result": necessity_result,
                "evidence": [],
                "reason": "fixture",
            },
        },
    }


def qualification_status(discovery_data: dict, handoff: dict | None) -> str:
    artifact = qualification.build_artifact(
        framework="flutter",
        candidate_name="ExamplePlugin",
        discovery=discovery_data,
        handoff=handoff,
    )
    return artifact["qualification"]["status"]


def test_candidate_qualification_states() -> None:
    assert qualification_status(
        discovery_fixture(),
        handoff_fixture(library_result="needs_adaptation"),
    ) == "RECOMMENDED"

    assert qualification_status(
        discovery_fixture(required_result="partial"),
        handoff_fixture(library_result="needs_adaptation"),
    ) == "NEEDS_OFFICIAL_CHECK"

    assert qualification_status(
        discovery_fixture(),
        handoff_fixture(library_result="adapted", necessity_result="needed"),
    ) == "EXCLUDED_ALREADY_ADAPTED"

    assert qualification_status(
        discovery_fixture(),
        handoff_fixture(library_result="no_adaptation_needed"),
    ) == "EXCLUDED_NO_ADAPTATION_NEEDED"

    assert qualification_status(
        discovery_fixture(
            matches=[
                {
                    "source": "CPF-Flutter",
                    "match": "fluttertpc_ExamplePlugin",
                    "kind": "canonical_repository_name",
                }
            ]
        ),
        handoff_fixture(library_result="needs_adaptation"),
    ) == "EXCLUDED_ALREADY_ADAPTED"

    assert qualification_status(discovery_fixture(), None) == "NEEDS_OFFICIAL_CHECK"


def test_missing_candidate_is_unverifiable() -> None:
    artifact = qualification.build_artifact(
        framework="flutter",
        candidate_name="MissingPlugin",
        discovery=discovery_fixture(),
        handoff=None,
    )
    assert artifact["qualification"]["status"] == "EXCLUDED_UNVERIFIABLE"
    assert artifact["qualification"]["eligible_to_start_adaptation"] is False


def main() -> None:
    test_dedup_identity()
    test_result_specific_guardrails()
    test_positive_adaptation_evidence()
    test_candidate_qualification_states()
    test_missing_candidate_is_unverifiable()

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_pubspec_name_parser(Path(tmp))

    print(
        "DETERMINISTIC TESTS PASSED: discovery helpers, official handoff guardrails, "
        "and candidate qualification states"
    )


if __name__ == "__main__":
    main()
