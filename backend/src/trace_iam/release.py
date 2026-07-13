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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        evidence = ManualConditionalAccessEvidence(
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
        item, facts = normalize_manual_evidence(evidence)
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
        evidence = ManualResourceAssignmentEvidence(
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
        item, facts = normalize_resource_assignment_evidence(evidence)
        investigation = Investigation(
            id=investigation_id,
            title=title,
            scenario_type=scenario,
            affected_subject=evidence.subject,
            affected_resource=evidence.resource,
            evidence_items=(item,),
        )
        return (
            investigation,
            AnalysisContext(investigation=investigation, facts=facts),
            (MissingResourceAssignmentRule(),),
        )

    evidence = ManualGuestB2BEvidence(
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
    item, facts = normalize_guest_b2b_evidence(evidence)
    investigation = Investigation(
        id=investigation_id,
        title=title,
        scenario_type=scenario,
        affected_subject=evidence.guest_subject,
        affected_resource=evidence.resource,
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
        json_path.write_text(
            json.dumps(
                report.json_report,
                default=_json_default,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(report.markdown_report, encoding="utf-8")
        manifest_entries.append(
            {
                "scenario": scenario_path.name,
                "scenario_type": investigation.scenario_type.value,
                "investigation_id": investigation.id,
                "evaluated_rule_ids": list(outcome.evaluated_rule_ids),
                "finding_count": len(outcome.findings),
                "scenario_sha256": _sha256(scenario_path),
                "json_report": json_path.name,
                "json_report_sha256": _sha256(json_path),
                "markdown_report": markdown_path.name,
                "markdown_report_sha256": _sha256(markdown_path),
                "findings": [asdict(finding) for finding in outcome.findings],
            }
        )

    if len(manifest_entries) != 3:
        raise RuntimeError(
            "Release proof requires exactly three public-safe scenarios; "
            f"found {len(manifest_entries)}"
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
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
        encoding="utf-8",
    )
    return manifest_path
