from dataclasses import dataclass

from trace_iam.domain import Confidence, EvidenceFact, EvidenceItem, EvidenceKind


@dataclass(frozen=True, slots=True)
class ManualGuestB2BEvidence:
    evidence_id: str
    source: str
    guest_subject: str
    resource: str
    invitation_sent: bool
    invitation_redeemed: bool
    tenant_restriction_observed: bool
    resource_assignment_present: bool
    restriction_detail: str | None = None
    redacted: bool = True

    def __post_init__(self) -> None:
        for label, value in (
            ("Evidence id", self.evidence_id),
            ("Evidence source", self.source),
            ("Guest subject", self.guest_subject),
            ("Resource", self.resource),
        ):
            if not value.strip():
                raise ValueError(f"{label} must not be blank")
        if not self.redacted:
            raise ValueError("TRACE accepts only redacted guest B2B evidence")


def normalize_guest_b2b_evidence(
    evidence: ManualGuestB2BEvidence,
) -> tuple[EvidenceItem, tuple[EvidenceFact, ...]]:
    item = EvidenceItem(
        id=evidence.evidence_id,
        kind=EvidenceKind.MANUAL_STRUCTURED,
        source=evidence.source,
        subject=evidence.guest_subject,
        resource=evidence.resource,
        redacted=evidence.redacted,
    )
    facts = [
        EvidenceFact(
            fact_type="guest_invitation_sent",
            value=evidence.invitation_sent,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="guest_invitation_redeemed",
            value=evidence.invitation_redeemed,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="guest_tenant_restriction_observed",
            value=evidence.tenant_restriction_observed,
            source_evidence_id=evidence.evidence_id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="guest_resource_assignment_present",
            value=evidence.resource_assignment_present,
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
    if evidence.restriction_detail is not None and evidence.restriction_detail.strip():
        facts.append(
            EvidenceFact(
                fact_type="guest_tenant_restriction_detail",
                value=evidence.restriction_detail.strip(),
                source_evidence_id=evidence.evidence_id,
                certainty=Confidence.MEDIUM,
            )
        )
    return item, tuple(facts)
