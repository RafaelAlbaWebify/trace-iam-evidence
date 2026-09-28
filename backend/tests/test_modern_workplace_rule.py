from trace_iam.domain import AnalysisContext, Confidence, EvidenceFact, Investigation, ScenarioType
from trace_iam.rules.modern_workplace import ModernWorkplaceComplianceCorrelationRule


def fact(kind: str, value: str | int | bool) -> EvidenceFact:
    return EvidenceFact(kind, value, "graph-redacted", Confidence.HIGH)


def test_modern_workplace_rule_supports_correlation_not_causation() -> None:
    context = AnalysisContext(
        Investigation("trace-graph-demo", "Graph compliance review", ScenarioType.CONDITIONAL_ACCESS),
        (
            fact("conditional_access_failed", True),
            fact("conditional_access_policy_name", "Require compliant device"),
            fact("sign_in_device_compliant", False),
            fact("intune_compliance_state", "noncompliant"),
            fact("intune_last_sync", "2026-09-27T08:10:00Z"),
        ),
    )
    result = ModernWorkplaceComplianceCorrelationRule().evaluate(context)
    assert result.matched
    assert result.finding is not None
    assert result.finding.confidence is Confidence.HIGH
    assert "does not prove" in result.finding.limitations[0]
    assert "Do not disable Conditional Access" in result.finding.non_actions[0].description


def test_modern_workplace_rule_requires_ca_failure_and_device_signal() -> None:
    context = AnalysisContext(
        Investigation("trace-graph-demo", "Graph compliance review", ScenarioType.CONDITIONAL_ACCESS),
        (fact("conditional_access_failed", True),),
    )
    assert not ModernWorkplaceComplianceCorrelationRule().evaluate(context).matched
