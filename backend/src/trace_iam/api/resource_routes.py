from dataclasses import asdict, replace
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from trace_iam.api.case_guard import require_matching_case
from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Investigation, InvestigationStatus, ScenarioType
from trace_iam.evidence import (
    ManualResourceAssignmentEvidence,
    normalize_resource_assignment_evidence,
)
from trace_iam.persistence import InvestigationRepository
from trace_iam.persistence.runtime import get_repository
from trace_iam.reporting import build_report
from trace_iam.rules import MissingResourceAssignmentRule

router = APIRouter(prefix="/api/investigations", tags=["resource-assignment"])


class ResourceAssignmentRequest(BaseModel):
    investigation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    access_failed: bool
    assignment_required: bool
    assignment_present: bool
    assignment_name: str | None = Field(default=None, min_length=1)
    redacted: bool = True

    @field_validator("redacted")
    @classmethod
    def require_redacted_evidence(cls, value: bool) -> bool:
        if not value:
            raise ValueError("TRACE accepts only redacted resource-assignment evidence")
        return value


class ResourceAssignmentResponse(BaseModel):
    investigation_id: str
    run_number: int
    evaluated_rule_ids: list[str]
    finding_count: int
    json_report: dict[str, Any]
    markdown_report: str


@router.post("/analyze-resource-assignment", response_model=ResourceAssignmentResponse)
def analyze_resource_assignment(
    request: ResourceAssignmentRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> ResourceAssignmentResponse:
    existing = require_matching_case(
        request.investigation_id,
        request.title,
        ScenarioType.RESOURCE_ASSIGNMENT,
        repository,
    )
    manual_evidence = ManualResourceAssignmentEvidence(
        evidence_id=request.evidence_id,
        source=request.source,
        subject=request.subject,
        resource=request.resource,
        access_failed=request.access_failed,
        assignment_required=request.assignment_required,
        assignment_present=request.assignment_present,
        assignment_name=request.assignment_name,
        redacted=request.redacted,
    )
    evidence_item, facts = normalize_resource_assignment_evidence(manual_evidence)
    investigation = Investigation(
        id=request.investigation_id,
        title=request.title,
        scenario_type=ScenarioType.RESOURCE_ASSIGNMENT,
        priority=existing.priority if existing else Investigation.__dataclass_fields__["priority"].default,
        external_reference=existing.external_reference if existing else None,
        summary=existing.summary if existing else None,
        affected_subject=request.subject,
        affected_resource=request.resource,
        evidence_items=(evidence_item,),
        created_at=existing.created_at if existing else datetime.utcnow(),
    )
    outcome = analyze(
        AnalysisContext(investigation=investigation, facts=facts),
        [MissingResourceAssignmentRule()],
    )
    analyzed_investigation = replace(investigation, status=InvestigationStatus.ANALYZED)
    report = build_report(analyzed_investigation, outcome)
    repository.save_investigation(analyzed_investigation)
    stored_run = repository.append_analysis_run(
        analyzed_investigation.id,
        ruleset_version="RA-001@1.0.0",
        facts=facts,
        findings=[asdict(finding) for finding in outcome.findings],
        report_json=report.json_report,
        report_markdown=report.markdown_report,
    )
    return ResourceAssignmentResponse(
        investigation_id=analyzed_investigation.id,
        run_number=stored_run.run_number,
        evaluated_rule_ids=list(outcome.evaluated_rule_ids),
        finding_count=len(outcome.findings),
        json_report=report.json_report,
        markdown_report=report.markdown_report,
    )
