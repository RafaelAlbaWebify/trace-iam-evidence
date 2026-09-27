from trace_iam.evidence.graph_snapshot import normalize_graph_snapshot


def test_graph_snapshot_correlates_entra_ca_and_intune_without_claiming_cause() -> None:
    result = normalize_graph_snapshot(
        sign_ins=(
            {
                "id": "signin-redacted-001",
                "createdDateTime": "2026-09-27T08:15:00Z",
                "conditionalAccessStatus": "failure",
                "status": {"errorCode": 53000, "failureReason": "Device is not in required device state."},
                "deviceDetail": {"isManaged": True, "isCompliant": False},
                "appliedConditionalAccessPolicies": [
                    {"displayName": "Require compliant device", "result": "failure"}
                ],
            },
        ),
        policies=(
            {"id": "policy-redacted-001", "displayName": "Require compliant device", "state": "enabled"},
        ),
        managed_devices=(
            {
                "id": "device-redacted-001",
                "complianceState": "noncompliant",
                "managementAgent": "mdm",
                "lastSyncDateTime": "2026-09-27T08:10:00Z",
            },
        ),
    )
    fact_map = [(fact.fact_type, fact.value) for fact in result.facts]
    assert ("conditional_access_failed", True) in fact_map
    assert ("conditional_access_policy_name", "Require compliant device") in fact_map
    assert ("sign_in_device_compliant", False) in fact_map
    assert ("intune_compliance_state", "noncompliant") in fact_map
    assert len(result.evidence_items) == 3
    assert all(item.redacted for item in result.evidence_items)
    assert all(item.original_excerpt is None for item in result.evidence_items)
