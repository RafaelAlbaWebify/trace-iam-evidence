from datetime import datetime

from trace_iam.comparison import compare_runs
from trace_iam.domain import EvidenceItem, EvidenceKind
from trace_iam.persistence.repository import StoredAnalysisRun


def stored_run(
    run_number: int,
    *,
    ruleset_version: str,
    findings: list[dict[str, object]],
    evidence_ids: tuple[str, ...],
) -> StoredAnalysisRun:
    return StoredAnalysisRun(
        run_number=run_number,
        created_at=datetime(2026, 7, 14, 12, run_number),
        ruleset_version=ruleset_version,
        facts=(),
        evidence_snapshot=tuple(
            EvidenceItem(
                id=evidence_id,
                kind=EvidenceKind.GENERIC_TEXT_EXCERPT,
                source="Redacted comparison fixture",
            )
            for evidence_id in evidence_ids
        ),
        findings=findings,
        report_json={},
        report_markdown="# Report",
    )


def test_compare_runs_identifies_added_resolved_changed_and_evidence_deltas() -> None:
    base = stored_run(
        1,
        ruleset_version="CA-001@1.0.0",
        evidence_ids=("evidence-a", "evidence-b"),
        findings=[
            {"finding_id": "stable", "rule_id": "CA-001", "severity": "medium", "confidence": "medium"},
            {"finding_id": "resolved", "rule_id": "CA-002", "severity": "low", "confidence": "low"},
        ],
    )
    target = stored_run(
        2,
        ruleset_version="CA-001@1.1.0",
        evidence_ids=("evidence-b", "evidence-c"),
        findings=[
            {"finding_id": "stable", "rule_id": "CA-001", "severity": "high", "confidence": "high"},
            {"finding_id": "added", "rule_id": "CA-003", "severity": "medium", "confidence": "high"},
        ],
    )

    comparison = compare_runs(base, target)

    assert comparison.ruleset_changed is True
    assert [item["finding_id"] for item in comparison.added_findings] == ["added"]
    assert [item["finding_id"] for item in comparison.resolved_findings] == ["resolved"]
    assert comparison.changed_findings[0].identity == "stable"
    assert comparison.changed_findings[0].changed_fields == ("confidence", "severity")
    assert comparison.added_evidence_ids == ("evidence-c",)
    assert comparison.removed_evidence_ids == ("evidence-a",)
    assert comparison.unchanged_finding_count == 0
