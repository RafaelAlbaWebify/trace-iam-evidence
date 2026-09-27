from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from trace_iam.domain import Confidence, EvidenceFact, EvidenceItem, EvidenceKind, EvidenceReliability


@dataclass(frozen=True, slots=True)
class NormalizedGraphEvidence:
    evidence_items: tuple[EvidenceItem, ...]
    facts: tuple[EvidenceFact, ...]


def normalize_graph_snapshot(
    *,
    sign_ins: tuple[dict[str, Any], ...],
    policies: tuple[dict[str, Any], ...],
    managed_devices: tuple[dict[str, Any], ...],
) -> NormalizedGraphEvidence:
    items: list[EvidenceItem] = []
    facts: list[EvidenceFact] = []
    for index, sign_in in enumerate(sign_ins, start=1):
        evidence_id = f"graph-signin-{_safe_id(sign_in.get('id'), index)}"
        items.append(_item(evidence_id, "Microsoft Graph /auditLogs/signIns", sign_in))
        ca_status = sign_in.get("conditionalAccessStatus")
        if isinstance(ca_status, str):
            facts.append(_fact("conditional_access_status", ca_status, evidence_id))
            if ca_status.lower() == "failure":
                facts.append(_fact("conditional_access_failed", True, evidence_id))
            if ca_status.lower() == "success":
                facts.append(_fact("conditional_access_succeeded", True, evidence_id))
        status = sign_in.get("status")
        if isinstance(status, Mapping):
            error_code = status.get("errorCode")
            if isinstance(error_code, int):
                facts.append(_fact("sign_in_error_code", error_code, evidence_id))
            failure_reason = status.get("failureReason")
            if isinstance(failure_reason, str) and failure_reason.strip():
                facts.append(_fact("sign_in_failure_reason", failure_reason, evidence_id))
        device = sign_in.get("deviceDetail")
        if isinstance(device, Mapping):
            compliant = device.get("isCompliant")
            if isinstance(compliant, bool):
                facts.append(_fact("sign_in_device_compliant", compliant, evidence_id))
            managed = device.get("isManaged")
            if isinstance(managed, bool):
                facts.append(_fact("sign_in_device_managed", managed, evidence_id))
        applied = sign_in.get("appliedConditionalAccessPolicies")
        if isinstance(applied, list):
            for policy in applied:
                if not isinstance(policy, Mapping):
                    continue
                name = policy.get("displayName")
                result = policy.get("result")
                if isinstance(name, str) and name.strip():
                    facts.append(_fact("conditional_access_policy_name", name, evidence_id))
                if isinstance(result, str) and result.strip():
                    facts.append(_fact("conditional_access_policy_result", result, evidence_id))

    for index, policy in enumerate(policies, start=1):
        evidence_id = f"graph-ca-policy-{_safe_id(policy.get('id'), index)}"
        items.append(_item(evidence_id, "Microsoft Graph /identity/conditionalAccess/policies", policy))
        name = policy.get("displayName")
        if isinstance(name, str) and name.strip():
            facts.append(_fact("configured_conditional_access_policy", name, evidence_id))

    for index, device in enumerate(managed_devices, start=1):
        evidence_id = f"graph-intune-device-{_safe_id(device.get('id'), index)}"
        items.append(_item(evidence_id, "Microsoft Graph /deviceManagement/managedDevices", device))
        compliance = device.get("complianceState")
        if isinstance(compliance, str) and compliance.strip():
            facts.append(_fact("intune_compliance_state", compliance, evidence_id))
        management_agent = device.get("managementAgent")
        if isinstance(management_agent, str) and management_agent.strip():
            facts.append(_fact("intune_management_agent", management_agent, evidence_id))
        last_sync = device.get("lastSyncDateTime")
        if isinstance(last_sync, str) and last_sync.strip():
            facts.append(_fact("intune_last_sync", last_sync, evidence_id))

    return NormalizedGraphEvidence(tuple(items), tuple(facts))


def _safe_id(value: object, fallback: int) -> str:
    if isinstance(value, str) and value.strip():
        return "".join(character for character in value if character.isalnum() or character in "-_")[:80]
    return str(fallback)


def _item(evidence_id: str, source: str, payload: Mapping[str, Any]) -> EvidenceItem:
    observed = _parse_datetime(payload.get("createdDateTime") or payload.get("lastSyncDateTime"))
    return EvidenceItem(
        id=evidence_id,
        kind=EvidenceKind.MICROSOFT_GRAPH,
        source=source,
        captured_at=observed,
        redacted=True,
        reliability=EvidenceReliability.HIGH,
        notes="Normalized read-only Microsoft Graph evidence; identifiers must be redacted before persistence.",
    )


def _fact(fact_type: str, value: str | int | bool, evidence_id: str) -> EvidenceFact:
    return EvidenceFact(fact_type=fact_type, value=value, source_evidence_id=evidence_id, certainty=Confidence.HIGH)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
