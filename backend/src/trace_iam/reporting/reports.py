from dataclasses import asdict, dataclass
from typing import Any

from trace_iam.application import AnalysisOutcome
from trace_iam.domain import Investigation


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    investigation_id: str
    json_report: dict[str, Any]
    markdown_report: str


def build_report(investigation: Investigation, outcome: AnalysisOutcome) -> AnalysisReport:
    findings = [asdict(finding) for finding in outcome.findings]
    json_report: dict[str, Any] = {
        "investigation": {
            "id": investigation.id,
            "title": investigation.title,
            "scenario_type": investigation.scenario_type.value,
        },
        "evaluated_rule_ids": list(outcome.evaluated_rule_ids),
        "findings": findings,
    }

    lines = [
        f"# TRACE Investigation Report: {investigation.title}",
        "",
        f"- Investigation ID: `{investigation.id}`",
        f"- Scenario: `{investigation.scenario_type.value}`",
        f"- Evaluated rules: {', '.join(outcome.evaluated_rule_ids) or 'None'}",
        "",
        "## Findings",
        "",
    ]

    if not outcome.findings:
        lines.append("No supported finding was produced from the supplied evidence.")
    else:
        for finding in outcome.findings:
            lines.extend(
                [
                    f"### {finding.title}",
                    "",
                    f"- Rule: `{finding.rule_id}` version `{finding.rule_version}`",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Confidence: `{finding.confidence.value}`",
                    f"- Supporting facts: {', '.join(finding.supporting_fact_types) or 'None'}",
                    f"- Contradicting facts: {', '.join(finding.contradicting_fact_types) or 'None'}",
                    f"- Missing facts: {', '.join(finding.missing_fact_types) or 'None'}",
                    "",
                    "#### Safe next checks",
                    "",
                ]
            )
            lines.extend(
                f"- {check.description} — {check.purpose}"
                for check in finding.recommended_checks
            )
            lines.extend(["", "#### Do not change yet", ""])
            lines.extend(
                f"- {non_action.description} — {non_action.reason}"
                for non_action in finding.non_actions
            )
            if finding.limitations:
                lines.extend(["", "#### Limitations", ""])
                lines.extend(f"- {limitation}" for limitation in finding.limitations)

    return AnalysisReport(
        investigation_id=investigation.id,
        json_report=json_report,
        markdown_report="\n".join(lines).rstrip() + "\n",
    )
