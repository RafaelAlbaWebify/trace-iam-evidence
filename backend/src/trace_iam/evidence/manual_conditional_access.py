from dataclasses import dataclass

from trace_iam.domain import Confidence, EvidenceFact, EvidenceItem, EvidenceKind


@dataclass(frozen=True, slots=True)
class ManualConditionalAccessEvidence:
    evidence_id: str
    source: str
    conditional_access_failed: bool
    conditional_access_succeeded: bool = False
    policy_name: str | None = None
    redacted: bool = True

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("Evidence id must not be blank")
        if not self.source.strip():
            raise ValueError("Evidence source must not be blank")
        if not self.redacted:
            raise ValueError("TRACE accepts only redacted manual evidence")
        if self.policy_name is not None and not self.policy_name.strip():
            raise ValueError("Policy name must not be blank when provided")


def normalize_manual_evidence(
    evidence: ManualConditionalAccessEvidence,
) -> tuple[EvidenceItem, tuple[EvidenceFact, ...]]:
    item = EvidenceItem(
        id=evidence.evidence_id,
        kind=EvidenceKind.MANUAL_STRUCTURED,
        source=evidence.source,
        redacted=evidence.redacted,
    )

    facts: list[EvidenceFact] = [
        EvidenceFact(
            fact_type="conditional_access_failed",
            value=evidence.conditional_access_failed,
            source_evidence_id=item.id,
            certainty=Confidence.HIGH,
        ),
        EvidenceFact(
            fact_type="conditional_access_succeeded",
            value=evidence.conditional_access_succeeded,
            source_evidence_id=item.id,
            certainty=Confidence.HIGH,
        ),
    ]
    if evidence.policy_name is not None:
        facts.append(
            EvidenceFact(
                fact_type="conditional_access_policy_name",
                value=evidence.policy_name,
                source_evidence_id=item.id,
                certainty=Confidence.HIGH,
            )
        )

    return item, tuple(facts)
