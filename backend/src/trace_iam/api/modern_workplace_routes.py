from dataclasses import asdict, replace
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from trace_iam.application import analyze
from trace_iam.domain import AnalysisContext, CasePriority, Investigation, InvestigationStatus, ScenarioType
from trace_iam.evidence import normalize_graph_snapshot
from trace_iam.graph import DelegatedGraphTokenProvider, GraphAuthConfig, GraphClient, GraphError
from trace_iam.persistence import InvestigationRepository
from trace_iam.persistence.runtime import get_repository
from trace_iam.reporting import build_report
from trace_iam.rules import ConditionalAccessFailureRule, ModernWorkplaceComplianceCorrelationRule

router = APIRouter(prefix="/api/modern-workplace", tags=["modern-workplace"])

DEMO_ID = "trace-modern-workplace-demo"


class LiveGraphRequest(BaseModel):
    investigation_id: str
    sign_in_filter: str
    managed_device_filter: str


class LiveGraphStatus(BaseModel):
    configured: bool
    mode: str = "delegated-read-only"
    scopes: list[str]
    limitation: str


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


@router.get("/graph/status", response_model=LiveGraphStatus)
def graph_status() -> LiveGraphStatus:
    configured = bool(os.getenv("TRACE_GRAPH_CLIENT_ID", "").strip() and os.getenv("TRACE_GRAPH_TENANT_ID", "").strip())
    return LiveGraphStatus(
        configured=configured,
        scopes=["AuditLog.Read.All", "Policy.Read.ConditionalAccess", "DeviceManagementManagedDevices.Read.All"],
        limitation="Live mode performs scoped read-only GET requests. Intune managed-device access requires tenant licensing and consent.",
    )


@router.post("/graph/collect", response_model=DemoResponse)
def collect_live_graph_evidence(
    request: LiveGraphRequest,
    repository: InvestigationRepository = Depends(get_repository),
) -> DemoResponse:
    investigation = repository.get_investigation(request.investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if investigation.scenario_type is not ScenarioType.CONDITIONAL_ACCESS:
        raise HTTPException(status_code=409, detail="Live Graph collection currently requires a Conditional Access investigation")
    client_id = os.getenv("TRACE_GRAPH_CLIENT_ID", "").strip()
    tenant_id = os.getenv("TRACE_GRAPH_TENANT_ID", "").strip()
    if not client_id or not tenant_id:
        raise HTTPException(status_code=503, detail="Live Graph is not configured. Set TRACE_GRAPH_CLIENT_ID and TRACE_GRAPH_TENANT_ID for a registered public client.")
    try:
        provider = DelegatedGraphTokenProvider(GraphAuthConfig(client_id, tenant_id))
        with GraphClient(provider) as graph:
            sign_ins = graph.list_sign_ins(filter_expression=request.sign_in_filter).values
            policies = graph.list_conditional_access_policies().values
            devices = graph.list_managed_devices(filter_expression=request.managed_device_filter).values
    except GraphError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "category": exc.category,
                "graph_status": exc.status_code,
                "message": str(exc),
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={"category": "identity_authentication", "message": str(exc)},
        ) from exc
    normalized = normalize_graph_snapshot(sign_ins=sign_ins, policies=policies, managed_devices=devices)
    live_case = replace(investigation, evidence_items=normalized.evidence_items)
    outcome = analyze(
        AnalysisContext(investigation=live_case, facts=normalized.facts),
        [ModernWorkplaceComplianceCorrelationRule(), ConditionalAccessFailureRule()],
    )
    analyzed = replace(live_case, status=InvestigationStatus.ANALYZED)
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
