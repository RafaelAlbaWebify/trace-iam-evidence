from dataclasses import dataclass

from trace_iam.domain import Confidence, EvidenceFact, EvidenceItem, EvidenceKind


@dataclass(frozen=True, slots=True)
class ManualResourceAssignmentEvidence:
    evidence_id: str
    source: str
    subject: str
    resource: str
    access_failed: bool
    assignment_required: bool
    assignment_present: bool
    assignment_name: str | None = None
    redacted: bool = True

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("Evidence id must not be blank")
        if not self.source.strip():
            raise ValueError("Evidence source must not be blank")
        if not self.subject.strip():
            raise ValueError("Evidence subject must not be blank")
        if not self.resource.strip():
            raise ValueError("Evidence resource must not be blank")
        if not self.redacted:
            raise ValueError("TRACE accepts only redacted resource-assignment evidence")


def normalize_resource_assignment_evidence(
    evidence: ManualResourceAssignmentEvidence,
) -> tuple[EvidenceItem, tuple[EvidenceFact, ...]]:
    item = EvidenceItem(
        id=evidence.evidence_id,
        kind=EvidenceKind.MANUAL_STRUCTURED,
        source=evidence.source,
        subject=evidence.subject,
        resource=evidence.resource,
        redacted=evidence.redacted,
    )
    facts = [
        EvidenceFact(
            fact_type="resource_access_failed",
            value=evidence.access_failed,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="resource_assignment_required",
            value=evidence.assignment_required,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="resource_assignment_present",
            value=evidence.assignment_present,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="resource_name",
            value=evidence.resource,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
    ]
    if evidence.assignment_name is not None and evidence.assignment_name.strip():
        facts.append(
            EvidenceFact(
                fact_type="resource_assignment_name",
                value=evidence.assignment_name.strip(),
                source_evidence_id=evidence.evidence_id,
                certainty=Confidence.HIGH,
            )
        )
    return item, tuple(facts)
