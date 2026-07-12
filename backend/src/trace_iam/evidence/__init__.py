"""Evidence adapters for TRACE investigations."""

from .manual_conditional_access import ManualConditionalAccessEvidence, normalize_manual_evidence

__all__ = ["ManualConditionalAccessEvidence", "normalize_manual_evidence"]
