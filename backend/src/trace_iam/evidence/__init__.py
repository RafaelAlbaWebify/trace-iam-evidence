"""Evidence adapters for TRACE investigations."""

from .entra_signin_csv import (
    EntraCsvValidationError,
    ParsedEntraCsv,
    parse_entra_signin_csv,
)
from .manual_conditional_access import ManualConditionalAccessEvidence, normalize_manual_evidence
from .manual_guest_b2b import ManualGuestB2BEvidence, normalize_guest_b2b_evidence
from .manual_resource_assignment import (
    ManualResourceAssignmentEvidence,
    normalize_resource_assignment_evidence,
)

__all__ = [
    "EntraCsvValidationError",
    "ManualConditionalAccessEvidence",
    "ManualGuestB2BEvidence",
    "ManualResourceAssignmentEvidence",
    "ParsedEntraCsv",
    "normalize_guest_b2b_evidence",
    "normalize_manual_evidence",
    "normalize_resource_assignment_evidence",
    "parse_entra_signin_csv",
]
