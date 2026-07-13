from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Confidence, Investigation, ScenarioType
from trace_iam.evidence import (
    ManualResourceAssignmentEvidence,
    normalize_resource_assignment_evidence,
)
from trace_iam.rules import ConditionalAccessFailureRule, MissingResourceAssignmentRule


def _context(
    evidence: ManualResourceAssignmentEvidence,
    scenario: ScenarioType = ScenarioType.RESOURCE_ASSIGNMENT,
) -> AnalysisContext:
    item, facts = normalize_resource_assignment_evidence(evidence)
    return AnalysisContext(
        investigation=Investigation(
            id="assignment-1",
            title="Review resource assignment",
            scenario_type=scenario,
            affected_subject=evidence.subject,
            affected_resource=evidence.resource,
            evidence_items=(item,),
        ),
        facts=facts,
    )


def test_missing_required_assignment_emits_supported_finding() -> None:
    context = _context(
        ManualResourceAssignmentEvidence(
            evidence_id="assignment-evidence-1",
            source="public-safe manual evidence",
            subject="redacted-user",
            resource="Finance application",
            access_failed=True,
            assignment_required=True,
            assignment_present=False,
            assignment_name="Finance App User",
        )
    )

    outcome = analyze(
        context,
        (ConditionalAccessFailureRule(), MissingResourceAssignmentRule()),
    )

    assert outcome.evaluated_rule_ids == ("CA-001", "RA-001")
    assert len(outcome.findings) == 1
    finding = outcome.findings[0]
    assert finding.rule_id == "RA-001"
    assert finding.confidence is Confidence.HIGH
    assert finding.missing_fact_types == ()
    assert finding.non_actions[0].description == (
        "Do not grant broad or tenant-wide privileges."
    )


def test_assignment_present_prevents_missing_assignment_finding() -> None:
    context = _context(
        ManualResourceAssignmentEvidence(
            evidence_id="assignment-evidence-2",
            source="public-safe manual evidence",
            subject="redacted-user",
            resource="Finance application",
            access_failed=True,
            assignment_required=True,
            assignment_present=True,
        )
    )

    outcome = analyze(context, (MissingResourceAssignmentRule(),))

    assert outcome.findings == ()


def test_resource_assignment_rule_stays_inside_its_scenario() -> None:
    context = _context(
        ManualResourceAssignmentEvidence(
            evidence_id="assignment-evidence-3",
            source="public-safe manual evidence",
            subject="redacted-user",
            resource="Finance application",
            access_failed=True,
            assignment_required=True,
            assignment_present=False,
        ),
        scenario=ScenarioType.CONDITIONAL_ACCESS,
    )

    outcome = analyze(context, (MissingResourceAssignmentRule(),))

    assert outcome.findings == ()


def test_resource_assignment_adapter_rejects_unredacted_evidence() -> None:
    try:
        ManualResourceAssignmentEvidence(
            evidence_id="assignment-evidence-4",
            source="public-safe manual evidence",
            subject="redacted-user",
            resource="Finance application",
            access_failed=True,
            assignment_required=True,
            assignment_present=False,
            redacted=False,
        )
    except ValueError as exc:
        assert str(exc) == "TRACE accepts only redacted resource-assignment evidence"
    else:
        raise AssertionError("Expected unredacted evidence to be rejected")
