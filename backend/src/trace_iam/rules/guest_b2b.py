from trace_iam.domain import (
    AnalysisContext,
    Confidence,
    Finding,
    NonAction,
    RecommendedCheck,
    RuleResult,
    ScenarioType,
    Severity,
)


class GuestInvitationNotRedeemedRule:
    rule_id = "GB-001"
    version = "1.0.0"
    priority = 80

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        if context.investigation.scenario_type is not ScenarioType.GUEST_B2B:
            return RuleResult(matched=False)
        invited = any(fact.value is True for fact in context.facts_of_type("guest_invitation_sent"))
        redeemed = any(
            fact.value is True for fact in context.facts_of_type("guest_invitation_redeemed")
        )
        if not invited or redeemed:
            return RuleResult(matched=False)
        finding = Finding(
            finding_id="finding-gb-001",
            rule_id=self.rule_id,
            rule_version=self.version,
            title="Guest invitation is present but redemption is not supported",
            severity=Severity.MEDIUM,
            confidence=Confidence.HIGH,
            supporting_fact_types=("guest_invitation_sent", "guest_invitation_redeemed"),
            recommended_checks=(
                RecommendedCheck(
                    description="Verify invitation state and redemption identity in the guest lifecycle record.",
                    purpose="Distinguish an unredeemed invitation from later tenant or resource access failures.",
                    risk=Severity.LOW,
                ),
            ),
            non_actions=(
                NonAction(
                    description="Do not recreate the guest or issue repeated invitations without checking the existing lifecycle.",
                    reason="Duplicate guest objects or invitations can obscure the original evidence and assignment path.",
                ),
            ),
        )
        return RuleResult(matched=True, finding=finding)


class GuestTenantRestrictionRule:
    rule_id = "GB-002"
    version = "1.0.0"
    priority = 100

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        if context.investigation.scenario_type is not ScenarioType.GUEST_B2B:
            return RuleResult(matched=False)
        restricted = any(
            fact.value is True
            for fact in context.facts_of_type("guest_tenant_restriction_observed")
        )
        if not restricted:
            return RuleResult(matched=False)
        detail = bool(context.facts_of_type("guest_tenant_restriction_detail"))
        finding = Finding(
            finding_id="finding-gb-002",
            rule_id=self.rule_id,
            rule_version=self.version,
            title="Cross-tenant restriction is supported by supplied evidence",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH if detail else Confidence.MEDIUM,
            supporting_fact_types=("guest_tenant_restriction_observed",),
            missing_fact_types=(() if detail else ("guest_tenant_restriction_detail",)),
            limitations=(
                "TRACE does not determine whether the restriction is correctly configured or approved for change.",
            ),
            recommended_checks=(
                RecommendedCheck(
                    description="Review the applicable inbound and outbound cross-tenant access settings with the owning administrators.",
                    purpose="Confirm the exact trust boundary and whether the observed restriction is intentional.",
                    risk=Severity.LOW,
                ),
            ),
            non_actions=(
                NonAction(
                    description="Do not weaken or bypass cross-tenant access controls from this evidence alone.",
                    reason="Any control change requires validated scope, security approval, and evidence from both tenant boundaries.",
                ),
            ),
        )
        return RuleResult(matched=True, finding=finding)


class GuestResourceAssignmentRule:
    rule_id = "GB-003"
    version = "1.0.0"
    priority = 70

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        if context.investigation.scenario_type is not ScenarioType.GUEST_B2B:
            return RuleResult(matched=False)
        redeemed = any(
            fact.value is True for fact in context.facts_of_type("guest_invitation_redeemed")
        )
        assigned = any(
            fact.value is True
            for fact in context.facts_of_type("guest_resource_assignment_present")
        )
        assignment_absent = any(
            fact.value is False
            for fact in context.facts_of_type("guest_resource_assignment_present")
        )
        restricted = any(
            fact.value is True
            for fact in context.facts_of_type("guest_tenant_restriction_observed")
        )
        if not redeemed or assigned or not assignment_absent or restricted:
            return RuleResult(matched=False)
        finding = Finding(
            finding_id="finding-gb-003",
            rule_id=self.rule_id,
            rule_version=self.version,
            title="Redeemed guest lacks the supplied resource assignment",
            severity=Severity.MEDIUM,
            confidence=Confidence.HIGH,
            supporting_fact_types=(
                "guest_invitation_redeemed",
                "guest_resource_assignment_present",
            ),
            recommended_checks=(
                RecommendedCheck(
                    description="Verify the guest's direct or group-derived assignment to the specific resource.",
                    purpose="Keep resource entitlement separate from invitation and cross-tenant policy state.",
                    risk=Severity.LOW,
                ),
            ),
            non_actions=(
                NonAction(
                    description="Do not assign unrelated directory roles or broad tenant access.",
                    reason="The evidence concerns one resource assignment only.",
                ),
            ),
        )
        return RuleResult(matched=True, finding=finding)
