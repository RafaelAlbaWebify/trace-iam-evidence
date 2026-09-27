from dataclasses import asdict, replace

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, CasePriority, Investigation, InvestigationStatus, ScenarioType
from trace_iam.evidence import normalize_graph_snapshot
from trace_iam.persistence import InvestigationRepository
from trace_iam.persistence.runtime import get_repository
from trace_iam.reporting import build_report
from trace_iam.rules import ConditionalAccessFailureRule, ModernWorkplaceComplianceCorrelationRule

router = APIRouter(prefix="/api/modern-workplace", tags=["modern-workplace"])

DEMO_ID = "trace-modern-workplace-demo"


class DemoResponse(BaseModel):
    investigation_id: str
    run_number: int
    finding_count: int
    evaluated_rule_ids: list[str]
    markdown_report: str
    json_report: dict[str, object]
    evidence_sources: list[str]


@router.post("/demo", response_model=DemoResponse)
def seed_modern_workplace_demo(
    repository: InvestigationRepository = Depends(get_repository),
) -> DemoResponse:
    normalized = normalize_graph_snapshot(
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
    existing = repository.get_investigation(DEMO_ID)
    investigation = Investigation(
        id=DEMO_ID,
        title="Managed device blocked by Conditional Access",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        status=InvestigationStatus.DRAFT,
        priority=CasePriority.HIGH,
        external_reference="INC-GRAPH-DEMO-001",
        summary=(
            "Public-safe Modern Workplace investigation: correlate Entra sign-in, "
            "Conditional Access and Intune compliance evidence."
        ),
        evidence_items=normalized.evidence_items,
        created_at=existing.created_at if existing else Investigation(DEMO_ID, "demo", ScenarioType.CONDITIONAL_ACCESS).created_at,
    )
    outcome = analyze(
        AnalysisContext(investigation=investigation, facts=normalized.facts),
        [ModernWorkplaceComplianceCorrelationRule(), ConditionalAccessFailureRule()],
    )
    analyzed = replace(investigation, status=InvestigationStatus.ANALYZED)
    report = build_report(analyzed, outcome)
    repository.save_investigation(analyzed)
    stored = repository.append_analysis_run(
        analyzed.id,
        ruleset_version="CA-001@1.0.0+CA-002@1.0.0",
        facts=normalized.facts,
        findings=[asdict(finding) for finding in outcome.findings],
        report_json=report.json_report,
        report_markdown=report.markdown_report,
    )
    return DemoResponse(
        investigation_id=analyzed.id,
        run_number=stored.run_number,
        finding_count=len(outcome.findings),
        evaluated_rule_ids=list(outcome.evaluated_rule_ids),
        markdown_report=report.markdown_report,
        json_report=report.json_report,
        evidence_sources=sorted({item.source for item in normalized.evidence_items}),
    )
