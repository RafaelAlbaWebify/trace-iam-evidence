from datetime import UTC, datetime

import pytest

from trace_iam.domain import (
    AnalysisContext,
    Confidence,
    EvidenceFact,
    EvidenceItem,
    EvidenceKind,
    Investigation,
    RuleResult,
    ScenarioType,
)


def test_analysis_context_returns_only_matching_fact_type() -> None:
    evidence = EvidenceItem(
        id="evidence-1",
        kind=EvidenceKind.MANUAL_STRUCTURED,
        source="operator form",
        captured_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    investigation = Investigation(
        id="investigation-1",
        title="Conditional Access sign-in review",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        evidence_items=(evidence,),
    )
    context = AnalysisContext(
        investigation=investigation,
        facts=(
            EvidenceFact(
                fact_type="authentication_succeeded",
                value=True,
                source_evidence_id=evidence.id,
                certainty=Confidence.HIGH,
            ),
            EvidenceFact(
                fact_type="conditional_access_failed",
                value=True,
                source_evidence_id=evidence.id,
                certainty=Confidence.HIGH,
            ),
        ),
    )

    matching = context.facts_of_type("conditional_access_failed")

    assert len(matching) == 1
    assert matching[0].value is True
    assert matching[0].source_evidence_id == "evidence-1"


def test_evidence_item_rejects_blank_identity() -> None:
    with pytest.raises(ValueError, match="id must not be blank"):
        EvidenceItem(
            id=" ",
            kind=EvidenceKind.MANUAL_STRUCTURED,
            source="operator form",
        )


def test_matched_rule_result_requires_a_finding() -> None:
    with pytest.raises(ValueError, match="must include a finding"):
        RuleResult(matched=True)
