from dataclasses import asdict, replace
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from trace_iam.application import AnalysisOutcome, analyze
from trace_iam.domain import (
    AnalysisContext,
    EvidenceFact,
    Investigation,
    InvestigationStatus,
    ScenarioType,
)
from trace_iam.evidence import (
    EntraCsvValidationError,
    ManualConditionalAccessEvidence,
    normalize_manual_evidence,
    parse_entra_signin_csv,
)
from trace_iam.persistence import InvestigationRepository
from trace_iam.persistence.runtime import get_repository
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

    @field_validator("redacted")
    @classmethod
    def require_redacted_evidence(cls, value: bool) -> bool:
        if not value:
            raise ValueError("TRACE accepts only redacted manual evidence")
        return value


class CsvConditionalAccessRequest(BaseModel):
    investigation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    csv_text: str = Field(min_length=1)


class AnalysisResponse(BaseModel):
    investigation_id: str
    run_number: int
    evaluated_rule_ids: list[str]
    finding_count: int
    json_report: dict[str, Any]
    markdown_report: str


class InvestigationSummaryResponse(BaseModel):
    investigation_id: str
    title: str
    scenario_type: str
    status: str
    created_at: datetime
    archived_at: datetime | None
    analysis_run_count: int


class InvestigationDetailResponse(BaseModel):
    investigation_id: str
    title: str
    scenario_type: str
    status: str
    created_at: datetime
    evidence_item_count: int
    analysis_run_count: int


class AnalysisRunSummaryResponse(BaseModel):
    run_number: int
    created_at: datetime
    ruleset_version: str
    finding_count: int


def _persisted_response(
    investigation: Investigation,
    facts: tuple[EvidenceFact, ...],
    outcome: AnalysisOutcome,
    repository: InvestigationRepository,
) -> AnalysisResponse:
    analyzed_investigation = replace(investigation, status=InvestigationStatus.ANALYZED)
    report = build_report(analyzed_investigation, outcome)
    repository.save_investigation(analyzed_investigation)
    stored_run = repository.append_analysis_run(
        analyzed_investigation.id,
        ruleset_version="CA-001@1.0.0",
        facts=facts,
        findings=[asdict(finding) for finding in outcome.findings],
        report_json=report.json_report,
        report_markdown=report.markdown_report,
    )
    return AnalysisResponse(
        investigation_id=analyzed_investigation.id,
        run_number=stored_run.run_number,
        evaluated_rule_ids=list(outcome.evaluated_rule_ids),
        finding_count=len(outcome.findings),
        json_report=report.json_report,
        markdown_report=report.markdown_report,
    )


@router.post("/analyze-conditional-access", response_model=AnalysisResponse)
def analyze_conditional_access(
    request: ManualConditionalAccessRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> AnalysisResponse:
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
    return _persisted_response(investigation, facts, outcome, repository)


@router.post("/analyze-conditional-access-csv", response_model=AnalysisResponse)
def analyze_conditional_access_csv(
    request: CsvConditionalAccessRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> AnalysisResponse:
    try:
        parsed = parse_entra_signin_csv(request.csv_text, request.source)
    except EntraCsvValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    investigation = Investigation(
        id=request.investigation_id,
        title=request.title,
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        evidence_items=parsed.evidence_items,
    )
    outcome = analyze(
        AnalysisContext(investigation=investigation, facts=parsed.facts),
        [ConditionalAccessFailureRule()],
    )
    return _persisted_response(investigation, parsed.facts, outcome, repository)


@router.get("", response_model=list[InvestigationSummaryResponse])
def list_investigations(
    include_archived: bool = Query(default=False),
    repository: InvestigationRepository = Depends(get_repository),
) -> list[InvestigationSummaryResponse]:
    return [
        InvestigationSummaryResponse(
            investigation_id=item.investigation_id,
            title=item.title,
            scenario_type=item.scenario_type,
            status=item.status.value,
            created_at=item.created_at,
            archived_at=item.archived_at,
            analysis_run_count=item.analysis_run_count,
        )
        for item in repository.list_investigations(include_archived=include_archived)
    ]


@router.get("/{investigation_id}", response_model=InvestigationDetailResponse)
def load_investigation(
    investigation_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> InvestigationDetailResponse:
    investigation = repository.get_investigation(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    runs = repository.list_analysis_runs(investigation_id)
    return InvestigationDetailResponse(
        investigation_id=investigation.id,
        title=investigation.title,
        scenario_type=investigation.scenario_type.value,
        status=investigation.status.value,
        created_at=investigation.created_at,
        evidence_item_count=len(investigation.evidence_items),
        analysis_run_count=len(runs),
    )


@router.get("/{investigation_id}/runs", response_model=list[AnalysisRunSummaryResponse])
def list_analysis_runs(
    investigation_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> list[AnalysisRunSummaryResponse]:
    if repository.get_investigation(investigation_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return [
        AnalysisRunSummaryResponse(
            run_number=run.run_number,
            created_at=run.created_at,
            ruleset_version=run.ruleset_version,
            finding_count=len(run.findings),
        )
        for run in repository.list_analysis_runs(investigation_id)
    ]


@router.get("/{investigation_id}/runs/{run_number}/report.json")
def export_json_report(
    investigation_id: str,
    run_number: int,
    repository: InvestigationRepository = Depends(get_repository),
) -> dict[str, Any]:
    run = repository.get_analysis_run(investigation_id, run_number)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run.report_json


@router.get(
    "/{investigation_id}/runs/{run_number}/report.md",
    response_class=PlainTextResponse,
)
def export_markdown_report(
    investigation_id: str,
    run_number: int,
    repository: InvestigationRepository = Depends(get_repository),
) -> str:
    run = repository.get_analysis_run(investigation_id, run_number)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return run.report_markdown


@router.post("/{investigation_id}/archive", response_model=InvestigationDetailResponse)
def archive_investigation(
    investigation_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> InvestigationDetailResponse:
    try:
        repository.archive_investigation(investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    return load_investigation(investigation_id, repository)


@router.post("/{investigation_id}/reopen", response_model=InvestigationDetailResponse)
def reopen_investigation(
    investigation_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> InvestigationDetailResponse:
    try:
        repository.reopen_investigation(investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Investigation not found") from exc
    return load_investigation(investigation_id, repository)
