from dataclasses import asdict, replace
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Investigation, InvestigationStatus, ScenarioType
from trace_iam.evidence import ManualGuestB2BEvidence, normalize_guest_b2b_evidence
from trace_iam.persistence import InvestigationRepository
from trace_iam.persistence.runtime import get_repository
from trace_iam.reporting import build_report
from trace_iam.rules import (
    GuestInvitationNotRedeemedRule,
    GuestResourceAssignmentRule,
    GuestTenantRestrictionRule,
)

router = APIRouter(prefix="/api/investigations", tags=["guest-b2b"])


class GuestB2BRequest(BaseModel):
    investigation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    guest_subject: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    invitation_sent: bool
    invitation_redeemed: bool
    tenant_restriction_observed: bool
    resource_assignment_present: bool
    restriction_detail: str | None = Field(default=None, min_length=1)
    redacted: bool = True

    @field_validator("redacted")
    @classmethod
    def require_redacted_evidence(cls, value: bool) -> bool:
        if not value:
            raise ValueError("TRACE accepts only redacted guest B2B evidence")
        return value


class GuestB2BResponse(BaseModel):
    investigation_id: str
    run_number: int
    evaluated_rule_ids: list[str]
    finding_count: int
    json_report: dict[str, Any]
    markdown_report: str


@router.post("/analyze-guest-b2b", response_model=GuestB2BResponse)
def analyze_guest_b2b(
    request: GuestB2BRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> GuestB2BResponse:
    evidence = ManualGuestB2BEvidence(**request.model_dump())
    item, facts = normalize_guest_b2b_evidence(evidence)
    investigation = Investigation(
        id=request.investigation_id,
        title=request.title,
        scenario_type=ScenarioType.GUEST_B2B,
        affected_subject=request.guest_subject,
        affected_resource=request.resource,
        evidence_items=(item,),
    )
    rules = (
        GuestTenantRestrictionRule(),
        GuestInvitationNotRedeemedRule(),
        GuestResourceAssignmentRule(),
    )
    outcome = analyze(AnalysisContext(investigation=investigation, facts=facts), rules)
    analyzed = replace(investigation, status=InvestigationStatus.ANALYZED)
    report = build_report(analyzed, outcome)
    repository.save_investigation(analyzed)
    stored = repository.append_analysis_run(
        analyzed.id,
        ruleset_version="GB-001@1.0.0+GB-002@1.0.0+GB-003@1.0.0",
        facts=facts,
        findings=[asdict(finding) for finding in outcome.findings],
        report_json=report.json_report,
        report_markdown=report.markdown_report,
    )
    return GuestB2BResponse(
        investigation_id=analyzed.id,
        run_number=stored.run_number,
        evaluated_rule_ids=list(outcome.evaluated_rule_ids),
        finding_count=len(outcome.findings),
        json_report=report.json_report,
        markdown_report=report.markdown_report,
    )
