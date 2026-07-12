import pytest

from trace_iam.evidence import EntraCsvValidationError, parse_entra_signin_csv


def test_entra_csv_normalizes_failure_and_success_rows() -> None:
    parsed = parse_entra_signin_csv(
        "Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy\n"
        "signin-1,failure,Device is not compliant,Require compliant device\n"
        "signin-2,success,,Require MFA\n",
        source="redacted Entra export",
    )

    assert tuple(item.id for item in parsed.evidence_items) == (
        "entra-signin-signin-1",
        "entra-signin-signin-2",
    )
    assert tuple(fact.fact_type for fact in parsed.facts) == (
        "conditional_access_failed",
        "conditional_access_policy_name",
        "conditional_access_failure_reason",
        "conditional_access_succeeded",
        "conditional_access_policy_name",
    )
    assert {fact.source_evidence_id for fact in parsed.facts} == {
        "entra-signin-signin-1",
        "entra-signin-signin-2",
    }


def test_entra_csv_rejects_missing_required_header() -> None:
    with pytest.raises(EntraCsvValidationError, match="missing required headers"):
        parse_entra_signin_csv(
            "Sign-in ID,Conditional Access Status,Failure Reason\n"
            "signin-1,failure,Device is not compliant\n",
            source="redacted Entra export",
        )


def test_entra_csv_rejects_unsupported_status_without_guessing() -> None:
    with pytest.raises(EntraCsvValidationError, match="unsupported Conditional Access Status"):
        parse_entra_signin_csv(
            "Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy\n"
            "signin-1,blocked,Device is not compliant,Require compliant device\n",
            source="redacted Entra export",
        )


def test_entra_csv_requires_at_least_one_data_row() -> None:
    with pytest.raises(EntraCsvValidationError, match="at least one data row"):
        parse_entra_signin_csv(
            "Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy\n",
            source="redacted Entra export",
        )
