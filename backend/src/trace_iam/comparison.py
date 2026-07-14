from dataclasses import dataclass
from typing import Any, cast

from trace_iam.persistence.repository import StoredAnalysisRun

JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class FindingChange:
    identity: str
    before: JsonObject
    after: JsonObject
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunComparison:
    base_run_number: int
    target_run_number: int
    base_ruleset_version: str
    target_ruleset_version: str
    ruleset_changed: bool
    added_findings: tuple[JsonObject, ...]
    resolved_findings: tuple[JsonObject, ...]
    changed_findings: tuple[FindingChange, ...]
    added_evidence_ids: tuple[str, ...]
    removed_evidence_ids: tuple[str, ...]
    unchanged_finding_count: int


def _finding_identity(finding: JsonObject) -> str:
    for key in ("finding_id", "rule_id", "title"):
        value = finding.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("Stored finding has no stable identity")


def _finding_map(findings: list[JsonObject]) -> dict[str, JsonObject]:
    mapped: dict[str, JsonObject] = {}
    for finding in findings:
        identity = _finding_identity(finding)
        if identity in mapped:
            raise ValueError(f"Duplicate finding identity {identity!r} in stored run")
        mapped[identity] = finding
    return mapped


def _changed_fields(before: JsonObject, after: JsonObject) -> tuple[str, ...]:
    keys = sorted(set(before) | set(after))
    return tuple(key for key in keys if before.get(key) != after.get(key))


def compare_runs(base: StoredAnalysisRun, target: StoredAnalysisRun) -> RunComparison:
    if base.run_number == target.run_number:
        raise ValueError("Run comparison requires two different run numbers")
    base_findings = _finding_map(cast(list[JsonObject], base.findings))
    target_findings = _finding_map(cast(list[JsonObject], target.findings))
    added_ids = sorted(target_findings.keys() - base_findings.keys())
    resolved_ids = sorted(base_findings.keys() - target_findings.keys())
    shared_ids = sorted(base_findings.keys() & target_findings.keys())
    changed: list[FindingChange] = []
    unchanged = 0
    for identity in shared_ids:
        fields = _changed_fields(base_findings[identity], target_findings[identity])
        if fields:
            changed.append(
                FindingChange(
                    identity=identity,
                    before=base_findings[identity],
                    after=target_findings[identity],
                    changed_fields=fields,
                )
            )
        else:
            unchanged += 1
    base_evidence = {item.id for item in base.evidence_snapshot}
    target_evidence = {item.id for item in target.evidence_snapshot}
    return RunComparison(
        base_run_number=base.run_number,
        target_run_number=target.run_number,
        base_ruleset_version=base.ruleset_version,
        target_ruleset_version=target.ruleset_version,
        ruleset_changed=base.ruleset_version != target.ruleset_version,
        added_findings=tuple(target_findings[identity] for identity in added_ids),
        resolved_findings=tuple(base_findings[identity] for identity in resolved_ids),
        changed_findings=tuple(changed),
        added_evidence_ids=tuple(sorted(target_evidence - base_evidence)),
        removed_evidence_ids=tuple(sorted(base_evidence - target_evidence)),
        unchanged_finding_count=unchanged,
    )
