from dataclasses import dataclass
from typing import Iterable

from trace_iam.domain import AnalysisContext, Finding, Rule


@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    evaluated_rule_ids: tuple[str, ...]
    findings: tuple[Finding, ...]

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)


def analyze(context: AnalysisContext, rules: Iterable[Rule]) -> AnalysisOutcome:
    ordered_rules = sorted(
        rules,
        key=lambda rule: (-rule.priority, rule.rule_id, rule.version),
    )
    findings: list[Finding] = []
    evaluated_rule_ids: list[str] = []

    for rule in ordered_rules:
        evaluated_rule_ids.append(rule.rule_id)
        result = rule.evaluate(context)
        if result.finding is not None:
            findings.append(result.finding)

    return AnalysisOutcome(
        evaluated_rule_ids=tuple(evaluated_rule_ids),
        findings=tuple(findings),
    )
