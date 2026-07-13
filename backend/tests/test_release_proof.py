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
