from trace_iam.domain import AnalysisContext, Confidence, Finding, NonAction, RecommendedCheck, RuleResult, ScenarioType, Severity


class ModernWorkplaceComplianceCorrelationRule:
    rule_id = "CA-002"
    version = "1.0.0"
    priority = 110

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        if context.investigation.scenario_type is not ScenarioType.CONDITIONAL_ACCESS:
            return RuleResult(matched=False)
        ca_failed = any(f.value is True for f in context.facts_of_type("conditional_access_failed"))
        sign_in_noncompliant = any(f.value is False for f in context.facts_of_type("sign_in_device_compliant"))
        intune_noncompliant = any(
            isinstance(f.value, str) and f.value.lower() == "noncompliant"
            for f in context.facts_of_type("intune_compliance_state")
        )
        if not ca_failed or not (sign_in_noncompliant or intune_noncompliant):
            return RuleResult(matched=False)
        policies = context.facts_of_type("conditional_access_policy_name")
        sync = context.facts_of_type("intune_last_sync")
        supporting = ["conditional_access_failed"]
        if sign_in_noncompliant:
            supporting.append("sign_in_device_compliant")
        if intune_noncompliant:
            supporting.append("intune_compliance_state")
        missing: list[str] = []
        if not policies:
            missing.append("conditional_access_policy_name")
        if not sync:
            missing.append("intune_last_sync")
        return RuleResult(
            matched=True,
            finding=Finding(
                finding_id="finding-ca-002",
                rule_id=self.rule_id,
                rule_version=self.version,
                title="Conditional Access failure correlates with noncompliant device evidence",
                severity=Severity.HIGH,
                confidence=Confidence.HIGH if sign_in_noncompliant and intune_noncompliant else Confidence.MEDIUM,
                supporting_fact_types=tuple(supporting),
                missing_fact_types=tuple(missing),
                limitations=(
                    "Correlation does not prove that Intune compliance caused the access failure.",
                    "Confirm the applied policy grant controls and the device identity before remediation.",
                ),
                recommended_checks=(
                    RecommendedCheck(
                        description="Confirm the applied Conditional Access policy and grant-control result in the matching Entra sign-in.",
                        purpose="Verify that compliant-device state was evaluated on this sign-in path.",
                        risk=Severity.LOW,
                    ),
                    RecommendedCheck(
                        description="Compare the Entra sign-in device identity with the Intune managed-device record and review its latest compliance evaluation.",
                        purpose="Avoid correlating the sign-in with the wrong or stale device record.",
                        risk=Severity.LOW,
                    ),
                ),
                non_actions=(
                    NonAction(
                        description="Do not disable Conditional Access or mark the device compliant manually.",
                        reason="The evidence supports a scoped compliance investigation, not a policy bypass or forced compliance state.",
                    ),
                ),
            ),
        )
