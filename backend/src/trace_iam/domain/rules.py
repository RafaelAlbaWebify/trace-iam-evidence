from dataclasses import dataclass
from typing import Protocol

from .models import AnalysisContext, Finding


@dataclass(frozen=True, slots=True)
class RuleResult:
    matched: bool
    finding: Finding | None = None

    def __post_init__(self) -> None:
        if self.matched and self.finding is None:
            raise ValueError("A matched rule result must include a finding")
        if not self.matched and self.finding is not None:
            raise ValueError("An unmatched rule result must not include a finding")


class Rule(Protocol):
    rule_id: str
    version: str
    priority: int

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        """Evaluate normalized evidence without performing external writes."""
        ...
