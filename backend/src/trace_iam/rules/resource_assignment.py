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


class MissingResourceAssignmentRule:
    rule_id = "RA-001"
    version = "1.0.0"
    priority = 90

    def evaluate(self, context: AnalysisContext) -> RuleResult:
        if context.investigation.scenario_type is not ScenarioType.RESOURCE_ASSIGNMENT:
            return RuleResult(matched=False)

        access_failed = self._has_true_fact(context, "resource_access_failed")
        assignment_required = self._has_true_fact(context, "resource_assignment_required")
        assignment_absent = self._has_false_fact(context, "resource_assignment_present")
        if not access_failed or not assignment_required or not assignment_absent:
            return RuleResult(matched=False)

        assignment_present = self._has_true_fact(context, "resource_assignment_present")
        assignment_named = bool(context.facts_of_type("resource_assignment_name"))
        confidence = Confidence.MEDIUM if assignment_present else Confidence.HIGH

        finding = Finding(
            finding_id="finding-ra-001",
            rule_id=self.rule_id,
            rule_version=self.version,
            title="Required resource assignment is not present in supplied evidence",
            severity=Severity.MEDIUM,
            confidence=confidence,
            supporting_fact_types=(
                "resource_access_failed",
                "resource_assignment_required",
                "resource_assignment_present",
            ),
            contradicting_fact_types=(
                ("resource_assignment_present",) if assignment_present else ()
            ),
            missing_fact_types=(() if assignment_named else ("resource_assignment_name",)),
            limitations=(
                "The rule evaluates supplied assignment evidence only and does not query the resource or directory.",
            ),
            recommended_checks=(
                RecommendedCheck(
                    description=(
                        "Verify the subject's direct and group-derived assignment to the specific resource."
                    ),
                    purpose=(
                        "Confirm whether the expected entitlement is absent, delayed, scoped incorrectly, or inherited through a group."
                    ),
                    risk=Severity.LOW,
                ),
            ),
            non_actions=(
                NonAction(
                    description="Do not grant broad or tenant-wide privileges.",
                    reason=(
                        "The evidence supports checking one subject-to-resource assignment, not expanding unrelated access."
                    ),
                ),
            ),
        )
        return RuleResult(matched=True, finding=finding)

    @staticmethod
    def _has_true_fact(context: AnalysisContext, fact_type: str) -> bool:
        return any(fact.value is True for fact in context.facts_of_type(fact_type))

    @staticmethod
    def _has_false_fact(context: AnalysisContext, fact_type: str) -> bool:
        return any(fact.value is False for fact in context.facts_of_type(fact_type))
