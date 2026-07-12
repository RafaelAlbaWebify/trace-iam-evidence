from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Investigation, ScenarioType
from trace_iam.evidence import ManualConditionalAccessEvidence, normalize_manual_evidence
from trace_iam.reporting import build_report
from trace_iam.rules import ConditionalAccessFailureRule

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class ManualConditionalAccessRequest(BaseModel):
    investigation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    conditional_access_failed: bool
    conditional_access_succeeded: bool = False
    policy_name: str | None = Field(default=None, min_length=1)
    redacted: bool = True


class AnalysisResponse(BaseModel):
    investigation_id: str
    evaluated_rule_ids: list[str]
    finding_count: int
    json_report: dict[str, Any]
    markdown_report: str


@router.post("/analyze-conditional-access", response_model=AnalysisResponse)
def analyze_conditional_access(request: ManualConditionalAccessRequest) -> AnalysisResponse:
    manual_evidence = ManualConditionalAccessEvidence(
        evidence_id=request.evidence_id,
        source=request.source,
        conditional_access_failed=request.conditional_access_failed,
        conditional_access_succeeded=request.conditional_access_succeeded,
        policy_name=request.policy_name,
        redacted=request.redacted,
    )
    evidence_item, facts = normalize_manual_evidence(manual_evidence)
    investigation = Investigation(
        id=request.investigation_id,
        title=request.title,
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        evidence_items=(evidence_item,),
    )
    outcome = analyze(
        AnalysisContext(investigation=investigation, facts=facts),
        [ConditionalAccessFailureRule()],
    )
    report = build_report(investigation, outcome)
    return AnalysisResponse(
        investigation_id=investigation.id,
        evaluated_rule_ids=list(outcome.evaluated_rule_ids),
        finding_count=len(outcome.findings),
        json_report=report.json_report,
        markdown_report=report.markdown_report,
    )
