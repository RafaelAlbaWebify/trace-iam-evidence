from dataclasses import asdict, replace
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from trace_iam.application import AnalysisOutcome, analyze
from trace_iam.domain import (
    AnalysisContext,
    CasePriority,
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


class CreateInvestigationRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    scenario_type: ScenarioType
    priority: CasePriority = CasePriority.NORMAL
    external_reference: str | None = Field(default=None, min_length=2, max_length=80)
    summary: str | None = Field(default=None, min_length=3, max_length=500)


class UpdateInvestigationRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    priority: CasePriority | None = None
    external_reference: str | None = Field(default=None, min_length=2, max_length=80)
    summary: str | None = Field(default=None, min_length=3, max_length=500)


class TransitionInvestigationRequest(BaseModel):
    status: InvestigationStatus


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
    priority: str
    external_reference: str | None
    summary: str | None
    created_at: datetime
    archived_at: datetime | None
    analysis_run_count: int


class InvestigationDetailResponse(BaseModel):
    investigation_id: str
    title: str
    scenario_type: str
    status: str
    priority: str
    external_reference: str | None
    summary: str | None
    created_at: datetime
    evidence_item_count: int
    analysis_run_count: int


class AnalysisRunSummaryResponse(BaseModel):
    run_number: int
    created_at: datetime
    ruleset_version: str
    finding_count: int


_ALLOWED_TRANSITIONS: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.DRAFT: frozenset({InvestigationStatus.EVIDENCE_VALIDATED}),
    InvestigationStatus.EVIDENCE_VALIDATED: frozenset({InvestigationStatus.DRAFT, InvestigationStatus.ANALYZED}),
    InvestigationStatus.ANALYZED: frozenset({InvestigationStatus.REVIEWED}),
    InvestigationStatus.REVIEWED: frozenset({InvestigationStatus.ANALYZED, InvestigationStatus.EXPORTED}),
    InvestigationStatus.EXPORTED: frozenset({InvestigationStatus.REVIEWED}),
    InvestigationStatus.ARCHIVED: frozenset(),
}


def _detail_response(
    investigation: Investigation,
    repository: InvestigationRepository,
) -> InvestigationDetailResponse:
    runs = repository.list_analysis_runs(investigation.id)
    return InvestigationDetailResponse(
        investigation_id=investigation.id,
        title=investigation.title,
        scenario_type=investigation.scenario_type.value,
        status=investigation.status.value,
        priority=investigation.priority.value,
        external_reference=investigation.external_reference,
        summary=investigation.summary,
        created_at=investigation.created_at,
        evidence_item_count=len(investigation.evidence_items),
        analysis_run_count=len(runs),
    )


def _require_investigation(
    investigation_id: str,
    repository: InvestigationRepository,
) -> Investigation:
    investigation = repository.get_investigation(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


def _require_matching_investigation(
    investigation_id: str,
    title: str,
    scenario_type: ScenarioType,
    repository: InvestigationRepository,
) -> Investigation | None:
    existing = repository.get_investigation(investigation_id)
    if existing is None:
        return None
    if existing.scenario_type is not scenario_type:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Investigation belongs to {existing.scenario_type.value}; "
                f"create or select a {scenario_type.value} investigation"
            ),
        )
    if existing.title != title:
        raise HTTPException(status_code=409, detail="Investigation title does not match the persisted case")
    if existing.status is InvestigationStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived investigations must be reopened before analysis")
    return existing


def _with_existing_metadata(investigation: Investigation, existing: Investigation | None) -> Investigation:
    if existing is None:
        return investigation
    return replace(
        investigation,
        priority=existing.priority,
        external_reference=existing.external_reference,
        summary=existing.summary,
        created_at=existing.created_at,
    )


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


@router.post("", response_model=InvestigationDetailResponse, status_code=201)
def create_investigation(
    request: CreateInvestigationRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> InvestigationDetailResponse:
    investigation = Investigation(
        id=f"trace-{uuid4().hex[:12]}",
        title=request.title.strip(),
        scenario_type=request.scenario_type,
        priority=request.priority,
        external_reference=request.external_reference.strip() if request.external_reference else None,
        summary=request.summary.strip() if request.summary else None,
    )
    repository.save_investigation(investigation)
    return _detail_response(investigation, repository)


@router.patch("/{investigation_id}", response_model=InvestigationDetailResponse)
def update_investigation(
    investigation_id: str,
    request: UpdateInvestigationRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> InvestigationDetailResponse:
    investigation = _require_investigation(investigation_id, repository)
    if investigation.status is InvestigationStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived investigations must be reopened before editing")
    updated = replace(
        investigation,
        title=request.title.strip() if request.title is not None else investigation.title,
        priority=request.priority if request.priority is not None else investigation.priority,
        external_reference=(request.external_reference.strip() if request.external_reference else investigation.external_reference),
        summary=request.summary.strip() if request.summary else investigation.summary,
    )
    repository.save_investigation(updated)
    return _detail_response(updated, repository)


@router.post("/{investigation_id}/transition", response_model=InvestigationDetailResponse)
def transition_investigation(
    investigation_id: str,
    request: TransitionInvestigationRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> InvestigationDetailResponse:
    investigation = _require_investigation(investigation_id, repository)
    allowed = _ALLOWED_TRANSITIONS[investigation.status]
    if request.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition investigation from {investigation.status.value} to {request.status.value}",
        )
    updated = replace(investigation, status=request.status)
    repository.save_investigation(updated)
    return _detail_response(updated, repository)


@router.post("/analyze-conditional-access", response_model=AnalysisResponse)
def analyze_conditional_access(
    request: ManualConditionalAccessRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> AnalysisResponse:
    existing = _require_matching_investigation(
        request.investigation_id,
        request.title,
        ScenarioType.CONDITIONAL_ACCESS,
        repository,
    )
    manual_evidence = ManualConditionalAccessEvidence(
        evidence_id=request.evidence_id,
        source=request.source,
        conditional_access_failed=request.conditional_access_failed,
        conditional_access_succeeded=request.conditional_access_succeeded,
        policy_name=request.policy_name,
        redacted=request.redacted,
    )
    evidence_item, facts = normalize_manual_evidence(manual_evidence)
    investigation = _with_existing_metadata(
        Investigation(
            id=request.investigation_id,
            title=request.title,
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
            evidence_items=(evidence_item,),
        ),
        existing,
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
    existing = _require_matching_investigation(
        request.investigation_id,
        request.title,
        ScenarioType.CONDITIONAL_ACCESS,
        repository,
    )
    try:
        parsed = parse_entra_signin_csv(request.csv_text, request.source)
    except EntraCsvValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    investigation = _with_existing_metadata(
        Investigation(
            id=request.investigation_id,
            title=request.title,
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
            evidence_items=parsed.evidence_items,
        ),
        existing,
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
            priority=item.priority.value,
            external_reference=item.external_reference,
            summary=item.summary,
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
    return _detail_response(_require_investigation(investigation_id, repository), repository)


@router.get("/{investigation_id}/runs", response_model=list[AnalysisRunSummaryResponse])
def list_analysis_runs(
    investigation_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> list[AnalysisRunSummaryResponse]:
    _require_investigation(investigation_id, repository)
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
