import hashlib
import json
import shutil
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, Investigation, Rule, ScenarioType
from trace_iam.evidence import (
    ManualConditionalAccessEvidence,
    ManualGuestB2BEvidence,
    ManualResourceAssignmentEvidence,
    normalize_guest_b2b_evidence,
    normalize_manual_evidence,
    normalize_resource_assignment_evidence,
)
from trace_iam.reporting import build_report
from trace_iam.rules import (
    ConditionalAccessFailureRule,
    GuestInvitationNotRedeemedRule,
    GuestResourceAssignmentRule,
    GuestTenantRestrictionRule,
    MissingResourceAssignmentRule,
)

JsonObject = dict[str, Any]


def _json_default(value: object) -> str:
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _write_text(path: Path, value: str) -> None:
    path.write_text(
        _normalize_text(value),
        encoding="utf-8",
        newline="\n",
    )


def _sha256_text(path: Path) -> str:
    normalized = _normalize_text(path.read_text(encoding="utf-8"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load(path: Path) -> JsonObject:
    return cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))


def _build_scenario(
    data: JsonObject,
) -> tuple[Investigation, AnalysisContext, tuple[Rule, ...]]:
    scenario = ScenarioType(cast(str, data["scenario_type"]))
    evidence_data = cast(JsonObject, data["evidence"])
    investigation_id = cast(str, data["investigation_id"])
    title = cast(str, data["title"])

    if scenario is ScenarioType.CONDITIONAL_ACCESS:
        ca_evidence = ManualConditionalAccessEvidence(
            evidence_id=cast(str, evidence_data["evidence_id"]),
            source=cast(str, evidence_data["source"]),
            conditional_access_failed=cast(
                bool, evidence_data["conditional_access_failed"]
            ),
            conditional_access_succeeded=cast(
                bool, evidence_data["conditional_access_succeeded"]
            ),
            policy_name=cast(str | None, evidence_data.get("policy_name")),
            redacted=cast(bool, evidence_data["redacted"]),
        )
        item, facts = normalize_manual_evidence(ca_evidence)
        investigation = Investigation(
            id=investigation_id,
            title=title,
            scenario_type=scenario,
            evidence_items=(item,),
        )
        return (
            investigation,
            AnalysisContext(investigation=investigation, facts=facts),
            (ConditionalAccessFailureRule(),),
        )

    if scenario is ScenarioType.RESOURCE_ASSIGNMENT:
        assignment_evidence = ManualResourceAssignmentEvidence(
            evidence_id=cast(str, evidence_data["evidence_id"]),
            source=cast(str, evidence_data["source"]),
            subject=cast(str, evidence_data["subject"]),
            resource=cast(str, evidence_data["resource"]),
            access_failed=cast(bool, evidence_data["access_failed"]),
            assignment_required=cast(bool, evidence_data["assignment_required"]),
            assignment_present=cast(bool, evidence_data["assignment_present"]),
            assignment_name=cast(str | None, evidence_data.get("assignment_name")),
            redacted=cast(bool, evidence_data["redacted"]),
        )
        item, facts = normalize_resource_assignment_evidence(assignment_evidence)
        investigation = Investigation(
            id=investigation_id,
            title=title,
            scenario_type=scenario,
            affected_subject=assignment_evidence.subject,
            affected_resource=assignment_evidence.resource,
            evidence_items=(item,),
        )
        return (
            investigation,
            AnalysisContext(investigation=investigation, facts=facts),
            (MissingResourceAssignmentRule(),),
        )

    guest_evidence = ManualGuestB2BEvidence(
        evidence_id=cast(str, evidence_data["evidence_id"]),
        source=cast(str, evidence_data["source"]),
        guest_subject=cast(str, evidence_data["guest_subject"]),
        resource=cast(str, evidence_data["resource"]),
        invitation_sent=cast(bool, evidence_data["invitation_sent"]),
        invitation_redeemed=cast(bool, evidence_data["invitation_redeemed"]),
        tenant_restriction_observed=cast(
            bool, evidence_data["tenant_restriction_observed"]
        ),
        resource_assignment_present=cast(
            bool, evidence_data["resource_assignment_present"]
        ),
        restriction_detail=cast(str | None, evidence_data.get("restriction_detail")),
        redacted=cast(bool, evidence_data["redacted"]),
    )
    item, facts = normalize_guest_b2b_evidence(guest_evidence)
    investigation = Investigation(
        id=investigation_id,
        title=title,
        scenario_type=scenario,
        affected_subject=guest_evidence.guest_subject,
        affected_resource=guest_evidence.resource,
        evidence_items=(item,),
    )
    return (
        investigation,
        AnalysisContext(investigation=investigation, facts=facts),
        (
            GuestTenantRestrictionRule(),
            GuestInvitationNotRedeemedRule(),
            GuestResourceAssignmentRule(),
        ),
    )


def build_release_proof(scenario_dir: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True)

    manifest_entries: list[JsonObject] = []
    for scenario_path in sorted(scenario_dir.glob("*.json")):
        investigation, context, rules = _build_scenario(_load(scenario_path))
        outcome = analyze(context, rules)
        report = build_report(investigation, outcome)
        stem = scenario_path.stem
        json_path = reports_dir / f"{stem}.json"
        markdown_path = reports_dir / f"{stem}.md"
        _write_text(
            json_path,
            json.dumps(
                report.json_report,
                default=_json_default,
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        _write_text(markdown_path, report.markdown_report)
        manifest_entries.append(
            {
                "scenario": scenario_path.name,
                "scenario_type": investigation.scenario_type.value,
                "investigation_id": investigation.id,
                "evaluated_rule_ids": list(outcome.evaluated_rule_ids),
                "finding_count": len(outcome.findings),
                "scenario_sha256": _sha256_text(scenario_path),
                "json_report": json_path.name,
                "json_report_sha256": _sha256_text(json_path),
                "markdown_report": markdown_path.name,
                "markdown_report_sha256": _sha256_text(markdown_path),
                "findings": [asdict(finding) for finding in outcome.findings],
            }
        )

    if len(manifest_entries) != 3:
        raise RuntimeError(
            "Release proof requires exactly three public-safe scenarios; "
            f"found {len(manifest_entries)}"
        )

    manifest_path = output_dir / "manifest.json"
    _write_text(
        manifest_path,
        json.dumps(
            {
                "format_version": "1.0",
                "scenario_count": len(manifest_entries),
                "scenarios": manifest_entries,
            },
            default=_json_default,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return manifest_path
