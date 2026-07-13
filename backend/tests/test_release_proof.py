import json
from pathlib import Path
from typing import Any, cast

import pytest

from trace_iam.release import build_release_proof

JsonObject = dict[str, Any]


def test_release_proof_builds_three_verified_scenarios(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    scenario_dir = repository_root / "examples" / "scenarios"
    output_dir = tmp_path / "release-proof"

    manifest_path = build_release_proof(scenario_dir, output_dir)

    manifest = cast(JsonObject, json.loads(manifest_path.read_text(encoding="utf-8")))
    scenarios = cast(list[JsonObject], manifest["scenarios"])
    assert manifest["format_version"] == "1.0"
    assert manifest["scenario_count"] == 3
    assert {item["scenario_type"] for item in scenarios} == {
        "conditional_access",
        "resource_assignment",
        "guest_b2b",
    }
    assert {rule_id for item in scenarios for rule_id in item["evaluated_rule_ids"]} >= {
        "CA-001",
        "RA-001",
        "GB-001",
        "GB-002",
        "GB-003",
    }
    assert all(item["finding_count"] >= 1 for item in scenarios)
    for item in scenarios:
        assert len(cast(str, item["scenario_sha256"])) == 64
        assert (output_dir / "reports" / cast(str, item["json_report"])).is_file()
        assert (output_dir / "reports" / cast(str, item["markdown_report"])).is_file()


def test_release_proof_is_stable_across_text_line_endings(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    source_dir = repository_root / "examples" / "scenarios"
    lf_dir = tmp_path / "lf-scenarios"
    crlf_dir = tmp_path / "crlf-scenarios"
    lf_dir.mkdir()
    crlf_dir.mkdir()

    for source_path in source_dir.glob("*.json"):
        normalized = source_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        lf_dir.joinpath(source_path.name).write_text(
            normalized,
            encoding="utf-8",
            newline="\n",
        )
        crlf_dir.joinpath(source_path.name).write_text(
            normalized,
            encoding="utf-8",
            newline="\r\n",
        )

    lf_output = tmp_path / "lf-proof"
    crlf_output = tmp_path / "crlf-proof"
    lf_manifest = build_release_proof(lf_dir, lf_output)
    crlf_manifest = build_release_proof(crlf_dir, crlf_output)

    assert lf_manifest.read_bytes() == crlf_manifest.read_bytes()
    for lf_report in sorted((lf_output / "reports").iterdir()):
        crlf_report = crlf_output / "reports" / lf_report.name
        assert lf_report.read_bytes() == crlf_report.read_bytes()


def test_release_proof_rejects_incomplete_scenario_pack(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    scenario_dir.joinpath("only-one.json").write_text(
        json.dumps(
            {
                "scenario_type": "conditional_access",
                "investigation_id": "incomplete-ca",
                "title": "Incomplete release pack",
                "evidence": {
                    "evidence_id": "incomplete-evidence",
                    "source": "public-safe test",
                    "conditional_access_failed": True,
                    "conditional_access_succeeded": False,
                    "redacted": True,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="exactly three public-safe scenarios"):
        build_release_proof(scenario_dir, tmp_path / "proof")
