from csv import DictReader
from dataclasses import dataclass
from io import StringIO

from trace_iam.domain import Confidence, EvidenceFact, EvidenceItem, EvidenceKind

REQUIRED_HEADERS = (
    "Sign-in ID",
    "Conditional Access Status",
    "Failure Reason",
    "Conditional Access Policy",
)
SUPPORTED_STATUSES = {"failure", "success", "notApplied"}


class EntraCsvValidationError(ValueError):
    """Raised when a supplied redacted Entra CSV does not match the documented contract."""


@dataclass(frozen=True, slots=True)
class ParsedEntraCsv:
    evidence_items: tuple[EvidenceItem, ...]
    facts: tuple[EvidenceFact, ...]


def parse_entra_signin_csv(csv_text: str, source: str) -> ParsedEntraCsv:
    if not source.strip():
        raise EntraCsvValidationError("CSV source must not be blank")
    if not csv_text.strip():
        raise EntraCsvValidationError("CSV content must not be blank")

    reader = DictReader(StringIO(csv_text))
    headers = reader.fieldnames
    if headers is None:
        raise EntraCsvValidationError("CSV header row is required")
    if len(headers) != len(set(headers)):
        raise EntraCsvValidationError("CSV headers must not contain duplicates")

    missing_headers = tuple(header for header in REQUIRED_HEADERS if header not in headers)
    if missing_headers:
        missing = ", ".join(missing_headers)
        raise EntraCsvValidationError(f"CSV is missing required headers: {missing}")

    evidence_items: list[EvidenceItem] = []
    facts: list[EvidenceFact] = []

    for row_number, row in enumerate(reader, start=2):
        sign_in_id = (row.get("Sign-in ID") or "").strip()
        status = (row.get("Conditional Access Status") or "").strip()
        failure_reason = (row.get("Failure Reason") or "").strip()
        policy_name = (row.get("Conditional Access Policy") or "").strip()

        if not sign_in_id:
            raise EntraCsvValidationError(f"Row {row_number}: Sign-in ID must not be blank")
        if status not in SUPPORTED_STATUSES:
            allowed = ", ".join(sorted(SUPPORTED_STATUSES))
            raise EntraCsvValidationError(
                f"Row {row_number}: unsupported Conditional Access Status {status!r}; "
                f"expected one of {allowed}"
            )

        evidence_id = f"entra-signin-{sign_in_id}"
        evidence_items.append(
            EvidenceItem(
                id=evidence_id,
                kind=EvidenceKind.ENTRA_SIGNIN_CSV,
                source=source,
                redacted=True,
            )
        )

        if status == "failure":
            facts.append(
                EvidenceFact(
                    fact_type="conditional_access_failed",
                    value=True,
                    source_evidence_id=evidence_id,
                    certainty=Confidence.HIGH,
                )
            )
        elif status == "success":
            facts.append(
                EvidenceFact(
                    fact_type="conditional_access_succeeded",
                    value=True,
                    source_evidence_id=evidence_id,
                    certainty=Confidence.HIGH,
                )
            )

        if policy_name:
            facts.append(
                EvidenceFact(
                    fact_type="conditional_access_policy_name",
                    value=policy_name,
                    source_evidence_id=evidence_id,
                    certainty=Confidence.HIGH,
                )
            )
        if failure_reason:
            facts.append(
                EvidenceFact(
                    fact_type="conditional_access_failure_reason",
                    value=failure_reason,
                    source_evidence_id=evidence_id,
                    certainty=Confidence.HIGH,
                )
            )

    if not evidence_items:
        raise EntraCsvValidationError("CSV must contain at least one data row")

    return ParsedEntraCsv(
        evidence_items=tuple(evidence_items),
        facts=tuple(facts),
    )
