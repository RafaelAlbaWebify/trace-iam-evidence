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


class ConditionalAccessFailureRule:
    rule_id = "CA-001"
    version = "1.0.0"
    priority = 100

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        if context.investigation.scenario_type is not ScenarioType.CONDITIONAL_ACCESS:
            return RuleResult(matched=False)

        failed = tuple(
            fact
            for fact in context.facts_of_type("conditional_access_failed")
            if fact.value is True
        )
        if not failed:
            return RuleResult(matched=False)

        succeeded = tuple(
            fact
            for fact in context.facts_of_type("conditional_access_succeeded")
            if fact.value is True
        )
        policy_names = tuple(
            fact
            for fact in context.facts_of_type("conditional_access_policy_name")
            if isinstance(fact.value, str) and fact.value.strip()
        )

        confidence = Confidence.MEDIUM if succeeded else Confidence.HIGH
        contradicting = ("conditional_access_succeeded",) if succeeded else ()
        missing = () if policy_names else ("conditional_access_policy_name",)
        limitations = (
            "Conflicting Conditional Access outcomes exist in the supplied evidence.",
        ) if succeeded else ()

        finding = Finding(
            finding_id="finding-ca-001",
            rule_id=self.rule_id,
            rule_version=self.version,
            title="Conditional Access failure is supported by supplied evidence",
            severity=Severity.HIGH,
            confidence=confidence,
            supporting_fact_types=("conditional_access_failed",),
            contradicting_fact_types=contradicting,
            missing_fact_types=missing,
            limitations=limitations,
            recommended_checks=(
                RecommendedCheck(
                    description="Review the matching Entra sign-in event and policy evaluation details.",
                    purpose="Confirm the exact policy, grant control, and affected sign-in path.",
                    risk=Severity.LOW,
                ),
            ),
            non_actions=(
                NonAction(
                    description="Do not disable Conditional Access globally.",
                    reason="The supplied evidence supports a scoped investigation, not a tenant-wide policy change.",
                ),
            ),
        )
        return RuleResult(matched=True, finding=finding)
