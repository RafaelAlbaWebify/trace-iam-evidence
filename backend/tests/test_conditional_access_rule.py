from trace_iam.application import analyze
from trace_iam.domain import (
    AnalysisContext,
    Confidence,
    EvidenceFact,
    Investigation,
    ScenarioType,
)
from trace_iam.rules import ConditionalAccessFailureRule


def make_context(*facts: EvidenceFact) -> AnalysisContext:
    return AnalysisContext(
        investigation=Investigation(
            id="investigation-ca-1",
            title="Conditional Access investigation",
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        ),
        facts=facts,
    )


def fact(fact_type: str, value: str | int | bool = True) -> EvidenceFact:
    return EvidenceFact(
        fact_type=fact_type,
        value=value,
        source_evidence_id="evidence-1",
        certainty=Confidence.HIGH,
    )


def test_conditional_access_failure_produces_supported_finding() -> None:
    outcome = analyze(
        make_context(
            fact("conditional_access_failed"),
            fact("conditional_access_policy_name", "Require compliant device"),
        ),
        [ConditionalAccessFailureRule()],
    )

    assert outcome.evaluated_rule_ids == ("CA-001",)
    assert outcome.has_findings is True
    finding = outcome.findings[0]
    assert finding.confidence is Confidence.HIGH
    assert finding.missing_fact_types == ()
    assert finding.contradicting_fact_types == ()
    assert finding.rule_version == "1.0.0"


def test_conflicting_outcomes_reduce_confidence_and_remain_visible() -> None:
    outcome = analyze(
        make_context(
            fact("conditional_access_failed"),
            fact("conditional_access_succeeded"),
        ),
        [ConditionalAccessFailureRule()],
    )

    finding = outcome.findings[0]
    assert finding.confidence is Confidence.MEDIUM
    assert finding.contradicting_fact_types == ("conditional_access_succeeded",)
    assert finding.missing_fact_types == ("conditional_access_policy_name",)
    assert finding.limitations


def test_missing_failure_fact_does_not_create_a_finding() -> None:
    outcome = analyze(
        make_context(fact("authentication_failed")),
        [ConditionalAccessFailureRule()],
    )

    assert outcome.evaluated_rule_ids == ("CA-001",)
    assert outcome.has_findings is False
    assert outcome.findings == ()


def test_rule_does_not_cross_scenario_boundary() -> None:
    context = AnalysisContext(
        investigation=Investigation(
            id="investigation-resource-1",
            title="Resource assignment investigation",
            scenario_type=ScenarioType.RESOURCE_ASSIGNMENT,
        ),
        facts=(fact("conditional_access_failed"),),
    )

    outcome = analyze(context, [ConditionalAccessFailureRule()])

    assert outcome.findings == ()
