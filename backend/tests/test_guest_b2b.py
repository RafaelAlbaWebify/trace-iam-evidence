from pathlib import Path

from fastapi.testclient import TestClient

from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Investigation, ScenarioType
from trace_iam.evidence import ManualGuestB2BEvidence, normalize_guest_b2b_evidence
from trace_iam.main import app
from trace_iam.persistence import InvestigationRepository, sqlite_engine
from trace_iam.persistence.runtime import get_repository, migrate_database
from trace_iam.rules import (
    GuestInvitationNotRedeemedRule,
    GuestResourceAssignmentRule,
    GuestTenantRestrictionRule,
)


def context(evidence: ManualGuestB2BEvidence) -> AnalysisContext:
    item, facts = normalize_guest_b2b_evidence(evidence)
    return AnalysisContext(
        investigation=Investigation(
            id="guest-1",
            title="Guest lifecycle review",
            scenario_type=ScenarioType.GUEST_B2B,
            evidence_items=(item,),
        ),
        facts=facts,
    )


def test_invitation_redemption_restriction_and_assignment_are_distinct() -> None:
    evidence = ManualGuestB2BEvidence(
        evidence_id="guest-evidence-1",
        source="public-safe evidence",
        guest_subject="redacted-guest",
        resource="Partner portal",
        invitation_sent=True,
        invitation_redeemed=True,
        tenant_restriction_observed=True,
        resource_assignment_present=False,
        restriction_detail="Inbound trust does not allow this tenant",
    )
    outcome = analyze(
        context(evidence),
        (
            GuestTenantRestrictionRule(),
            GuestInvitationNotRedeemedRule(),
            GuestResourceAssignmentRule(),
        ),
    )
    assert [finding.rule_id for finding in outcome.findings] == ["GB-002"]
    assert outcome.findings[0].non_actions[0].description == (
        "Do not weaken or bypass cross-tenant access controls from this evidence alone."
    )


def test_unredeemed_invitation_does_not_become_assignment_finding() -> None:
    evidence = ManualGuestB2BEvidence(
        evidence_id="guest-evidence-2",
        source="public-safe evidence",
        guest_subject="redacted-guest",
        resource="Partner portal",
        invitation_sent=True,
        invitation_redeemed=False,
        tenant_restriction_observed=False,
        resource_assignment_present=False,
    )
    outcome = analyze(
        context(evidence),
        (GuestInvitationNotRedeemedRule(), GuestResourceAssignmentRule()),
    )
    assert [finding.rule_id for finding in outcome.findings] == ["GB-001"]


def test_redeemed_guest_without_restriction_can_show_missing_assignment() -> None:
    evidence = ManualGuestB2BEvidence(
        evidence_id="guest-evidence-3",
        source="public-safe evidence",
        guest_subject="redacted-guest",
        resource="Partner portal",
        invitation_sent=True,
        invitation_redeemed=True,
        tenant_restriction_observed=False,
        resource_assignment_present=False,
    )
    outcome = analyze(context(evidence), (GuestResourceAssignmentRule(),))
    assert [finding.rule_id for finding in outcome.findings] == ["GB-003"]


def test_guest_api_persists_report_and_rejects_unredacted(tmp_path: Path) -> None:
    database_path = tmp_path / "guest.db"
    migrate_database(database_path)
    repository = InvestigationRepository(sqlite_engine(database_path))
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)
    payload = {
        "investigation_id": "guest-api-1",
        "title": "Guest tenant restriction",
        "evidence_id": "guest-api-evidence-1",
        "source": "public-safe API fixture",
        "guest_subject": "redacted-guest",
        "resource": "Partner portal",
        "invitation_sent": True,
        "invitation_redeemed": True,
        "tenant_restriction_observed": True,
        "resource_assignment_present": True,
        "restriction_detail": "Inbound trust restriction",
        "redacted": True,
    }
    try:
        response = client.post("/api/investigations/analyze-guest-b2b", json=payload)
        assert response.status_code == 200
        assert response.json()["run_number"] == 1
        assert response.json()["evaluated_rule_ids"] == ["GB-002", "GB-001", "GB-003"]
        assert response.json()["finding_count"] == 1
        assert "Do not weaken or bypass cross-tenant access controls" in response.json()[
            "markdown_report"
        ]
        assert repository.get_investigation("guest-api-1") is not None

        payload["redacted"] = False
        rejected = client.post("/api/investigations/analyze-guest-b2b", json=payload)
        assert rejected.status_code == 422
    finally:
        app.dependency_overrides.clear()
