from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias

FactValue: TypeAlias = str | int | bool


class ScenarioType(StrEnum):
    CONDITIONAL_ACCESS = "conditional_access"
    RESOURCE_ASSIGNMENT = "resource_assignment"
    GUEST_B2B = "guest_b2b"


class InvestigationStatus(StrEnum):
    DRAFT = "draft"
    EVIDENCE_VALIDATED = "evidence_validated"
    ANALYZED = "analyzed"
    REVIEWED = "reviewed"
    EXPORTED = "exported"
    ARCHIVED = "archived"


class CasePriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceKind(StrEnum):
    MANUAL_STRUCTURED = "manual_structured"
    ENTRA_SIGNIN_CSV = "entra_signin_csv"
    GENERIC_TEXT_EXCERPT = "generic_text_excerpt"


class EvidenceReliability(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    id: str
    kind: EvidenceKind
    source: str
    captured_at: datetime | None = None
    subject: str | None = None
    resource: str | None = None
    redacted: bool = True
    original_excerpt: str | None = None
    reliability: EvidenceReliability = EvidenceReliability.UNKNOWN
    notes: str | None = None
    validated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Evidence item id must not be blank")
        if not self.source.strip():
            raise ValueError("Evidence source must not be blank")
        if not self.redacted:
            raise ValueError("TRACE accepts only redacted evidence")
        if self.notes is not None and not self.notes.strip():
            raise ValueError("Evidence notes must not be blank")


@dataclass(frozen=True, slots=True)
class EvidenceFact:
    fact_type: str
    value: FactValue
    source_evidence_id: str
    certainty: Confidence
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.fact_type.strip():
            raise ValueError("Fact type must not be blank")
        if not self.source_evidence_id.strip():
            raise ValueError("Fact source evidence id must not be blank")


@dataclass(frozen=True, slots=True)
class RecommendedCheck:
    description: str
    purpose: str
    risk: Severity = Severity.LOW


@dataclass(frozen=True, slots=True)
class NonAction:
    description: str
    reason: str


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    rule_id: str
    rule_version: str
    title: str
    severity: Severity
    confidence: Confidence
    supporting_fact_types: tuple[str, ...]
    contradicting_fact_types: tuple[str, ...] = ()
    missing_fact_types: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    recommended_checks: tuple[RecommendedCheck, ...] = ()
    non_actions: tuple[NonAction, ...] = ()


@dataclass(frozen=True, slots=True)
class Investigation:
    id: str
    title: str
    scenario_type: ScenarioType
    status: InvestigationStatus = InvestigationStatus.DRAFT
    priority: CasePriority = CasePriority.NORMAL
    external_reference: str | None = None
    summary: str | None = None
    affected_subject: str | None = None
    affected_resource: str | None = None
    evidence_items: tuple[EvidenceItem, ...] = ()
    created_at: datetime = field(default_factory=datetime.utcnow)
    pre_archive_status: InvestigationStatus | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Investigation id must not be blank")
        if not self.title.strip():
            raise ValueError("Investigation title must not be blank")
        if self.external_reference is not None and not self.external_reference.strip():
            raise ValueError("External reference must not be blank")
        if self.summary is not None and not self.summary.strip():
            raise ValueError("Investigation summary must not be blank")
        if self.pre_archive_status is InvestigationStatus.ARCHIVED:
            raise ValueError("Pre-archive status cannot itself be archived")
        evidence_ids = [item.id for item in self.evidence_items]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence item ids must be unique within an investigation")


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    investigation: Investigation
    facts: tuple[EvidenceFact, ...]

    def facts_of_type(self, fact_type: str) -> tuple[EvidenceFact, ...]:
        return tuple(fact for fact in self.facts if fact.fact_type == fact_type)
