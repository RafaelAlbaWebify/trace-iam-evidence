from dataclasses import replace
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from trace_iam.domain import (
    EvidenceItem,
    EvidenceKind,
    EvidenceReliability,
    Investigation,
    InvestigationStatus,
)
from trace_iam.persistence import InvestigationRepository
from trace_iam.persistence.runtime import get_repository

router = APIRouter(prefix="/api/investigations/{investigation_id}/evidence", tags=["evidence"])


class EvidenceItemRequest(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=120)
    kind: EvidenceKind
    source: str = Field(min_length=2, max_length=200)
    captured_at: datetime | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    resource: str | None = Field(default=None, min_length=1, max_length=200)
    excerpt: str | None = Field(default=None, min_length=1, max_length=4000)
    reliability: EvidenceReliability = EvidenceReliability.UNKNOWN
    notes: str | None = Field(default=None, min_length=2, max_length=1000)
    redacted: bool = True

    @field_validator("redacted")
    @classmethod
    def require_redacted_evidence(cls, value: bool) -> bool:
        if not value:
            raise ValueError("TRACE accepts only redacted evidence")
        return value


class EvidenceMetadataRequest(BaseModel):
    source: str | None = Field(default=None, min_length=2, max_length=200)
    captured_at: datetime | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    resource: str | None = Field(default=None, min_length=1, max_length=200)
    reliability: EvidenceReliability | None = None
    notes: str | None = Field(default=None, min_length=2, max_length=1000)


class EvidenceItemResponse(BaseModel):
    evidence_id: str
    kind: str
    source: str
    captured_at: datetime | None
    subject: str | None
    resource: str | None
    excerpt: str | None
    reliability: str
    notes: str | None
    redacted: bool
    validated_at: datetime | None


def _require_investigation(
    investigation_id: str,
    repository: InvestigationRepository,
) -> Investigation:
    investigation = repository.get_investigation(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


def _require_editable(investigation: Investigation) -> None:
    if investigation.status is InvestigationStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived investigations must be reopened before evidence changes")


def _response(item: EvidenceItem) -> EvidenceItemResponse:
    return EvidenceItemResponse(
        evidence_id=item.id,
        kind=item.kind.value,
        source=item.source,
        captured_at=item.captured_at,
        subject=item.subject,
        resource=item.resource,
        excerpt=item.original_excerpt,
        reliability=item.reliability.value,
        notes=item.notes,
        redacted=item.redacted,
        validated_at=item.validated_at,
    )


@router.get("", response_model=list[EvidenceItemResponse])
def list_evidence(
    investigation_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> list[EvidenceItemResponse]:
    investigation = _require_investigation(investigation_id, repository)
    return [_response(item) for item in investigation.evidence_items]


@router.post("", response_model=EvidenceItemResponse, status_code=201)
def add_evidence(
    investigation_id: str,
    request: EvidenceItemRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> EvidenceItemResponse:
    investigation = _require_investigation(investigation_id, repository)
    _require_editable(investigation)
    evidence_id = request.evidence_id.strip()
    if any(item.id == evidence_id for item in investigation.evidence_items):
        raise HTTPException(status_code=409, detail="Evidence id already exists in this investigation")
    item = EvidenceItem(
        id=evidence_id,
        kind=request.kind,
        source=request.source.strip(),
        captured_at=request.captured_at,
        subject=request.subject.strip() if request.subject else None,
        resource=request.resource.strip() if request.resource else None,
        original_excerpt=request.excerpt.strip() if request.excerpt else None,
        reliability=request.reliability,
        notes=request.notes.strip() if request.notes else None,
        redacted=request.redacted,
    )
    updated = replace(
        investigation,
        evidence_items=(*investigation.evidence_items, item),
        status=(
            InvestigationStatus.DRAFT
            if investigation.status is InvestigationStatus.EVIDENCE_VALIDATED
            else investigation.status
        ),
    )
    repository.save_investigation(updated)
    return _response(item)


@router.patch("/{evidence_id}", response_model=EvidenceItemResponse)
def update_evidence_metadata(
    investigation_id: str,
    evidence_id: str,
    request: EvidenceMetadataRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> EvidenceItemResponse:
    investigation = _require_investigation(investigation_id, repository)
    _require_editable(investigation)
    existing = next((item for item in investigation.evidence_items if item.id == evidence_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    updated_item = replace(
        existing,
        source=request.source.strip() if request.source else existing.source,
        captured_at=request.captured_at if request.captured_at is not None else existing.captured_at,
        subject=request.subject.strip() if request.subject else existing.subject,
        resource=request.resource.strip() if request.resource else existing.resource,
        reliability=request.reliability if request.reliability is not None else existing.reliability,
        notes=request.notes.strip() if request.notes else existing.notes,
        validated_at=None,
    )
    items = tuple(updated_item if item.id == evidence_id else item for item in investigation.evidence_items)
    updated = replace(
        investigation,
        evidence_items=items,
        status=(
            InvestigationStatus.DRAFT
            if investigation.status is InvestigationStatus.EVIDENCE_VALIDATED
            else investigation.status
        ),
    )
    repository.save_investigation(updated)
    return _response(updated_item)


@router.post("/{evidence_id}/validate", response_model=EvidenceItemResponse)
def validate_evidence(
    investigation_id: str,
    evidence_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> EvidenceItemResponse:
    investigation = _require_investigation(investigation_id, repository)
    _require_editable(investigation)
    existing = next((item for item in investigation.evidence_items if item.id == evidence_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    validated = replace(
        existing,
        validated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    items = tuple(validated if item.id == evidence_id else item for item in investigation.evidence_items)
    all_validated = bool(items) and all(item.validated_at is not None for item in items)
    updated = replace(
        investigation,
        evidence_items=items,
        status=(
            InvestigationStatus.EVIDENCE_VALIDATED
            if all_validated and investigation.status is InvestigationStatus.DRAFT
            else investigation.status
        ),
    )
    repository.save_investigation(updated)
    return _response(validated)


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(
    investigation_id: str,
    evidence_id: str,
    repository: InvestigationRepository = Depends(get_repository),
) -> None:
    investigation = _require_investigation(investigation_id, repository)
    _require_editable(investigation)
    if repository.list_analysis_runs(investigation_id):
        raise HTTPException(status_code=409, detail="Evidence used by an immutable analysis history cannot be deleted")
    items = tuple(item for item in investigation.evidence_items if item.id != evidence_id)
    if len(items) == len(investigation.evidence_items):
        raise HTTPException(status_code=404, detail="Evidence item not found")
    repository.save_investigation(
        replace(investigation, evidence_items=items, status=InvestigationStatus.DRAFT)
    )
