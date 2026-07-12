from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Investigation, ScenarioType
from trace_iam.evidence import parse_entra_signin_csv
from trace_iam.rules import ConditionalAccessFailureRule


def test_redacted_entra_csv_drives_conditional_access_rule() -> None:
    parsed = parse_entra_signin_csv(
        "Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy\n"
        "signin-1,failure,Device is not compliant,Require compliant device\n",
        source="redacted Entra export",
    )
    investigation = Investigation(
        id="investigation-csv-1",
        title="Conditional Access CSV review",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        evidence_items=parsed.evidence_items,
    )

    outcome = analyze(
        AnalysisContext(investigation=investigation, facts=parsed.facts),
        [ConditionalAccessFailureRule()],
    )

    assert outcome.has_findings is True
    assert outcome.findings[0].rule_id == "CA-001"
    assert outcome.findings[0].missing_fact_types == ()
