from datetime import datetime, timedelta

from trace_iam.domain import CasePriority, InvestigationStatus, ScenarioType
from trace_iam.operational import build_operational_dashboard
from trace_iam.persistence.repository import InvestigationSummary


def summary(
    investigation_id: str,
    *,
    title: str,
    status: InvestigationStatus,
    priority: CasePriority,
    scenario: ScenarioType = ScenarioType.CONDITIONAL_ACCESS,
    reference: str | None = None,
) -> InvestigationSummary:
    return InvestigationSummary(
        investigation_id=investigation_id,
        title=title,
        scenario_type=scenario.value,
        status=status,
        priority=priority,
        external_reference=reference,
        summary=f"Redacted summary for {title}",
        created_at=datetime(2026, 7, 14, 8, 0),
        archived_at=datetime(2026, 7, 14, 9, 0) if status is InvestigationStatus.ARCHIVED else None,
        analysis_run_count=1 if status not in {InvestigationStatus.DRAFT, InvestigationStatus.EVIDENCE_VALIDATED} else 0,
    )


def test_dashboard_counts_real_operational_states_and_filters_cases() -> None:
    cases = (
        summary("trace-draft", title="Waiting access case", status=InvestigationStatus.DRAFT, priority=CasePriority.NORMAL, reference="INC-100"),
        summary("trace-ready", title="Validated guest case", status=InvestigationStatus.EVIDENCE_VALIDATED, priority=CasePriority.HIGH, scenario=ScenarioType.GUEST_B2B),
        summary("trace-review", title="Critical finance review", status=InvestigationStatus.REVIEWED, priority=CasePriority.CRITICAL, reference="INC-CRIT-7"),
        summary("trace-archived", title="Closed historical case", status=InvestigationStatus.ARCHIVED, priority=CasePriority.LOW),
    )
    latest = {
        "trace-draft": datetime(2026, 7, 14, 8, 30),
        "trace-ready": datetime(2026, 7, 14, 9, 0),
        "trace-review": datetime(2026, 7, 14, 10, 0),
        "trace-archived": datetime(2026, 7, 14, 7, 0),
    }

    dashboard = build_operational_dashboard(cases, latest_activity=latest, query="crit")

    assert dashboard.total_cases == 4
    assert dashboard.active_cases == 3
    assert dashboard.waiting_for_evidence == 1
    assert dashboard.ready_for_analysis == 1
    assert dashboard.under_review == 1
    assert dashboard.critical_active == 1
    assert dashboard.archived_cases == 1
    assert [item.investigation_id for item in dashboard.cases] == ["trace-review"]


def test_dashboard_orders_results_by_latest_immutable_activity() -> None:
    base = datetime(2026, 7, 14, 8, 0)
    cases = (
        summary("trace-one", title="First", status=InvestigationStatus.ANALYZED, priority=CasePriority.NORMAL),
        summary("trace-two", title="Second", status=InvestigationStatus.ANALYZED, priority=CasePriority.NORMAL),
    )

    dashboard = build_operational_dashboard(
        cases,
        latest_activity={"trace-one": base, "trace-two": base + timedelta(minutes=5)},
    )

    assert [item.investigation_id for item in dashboard.cases] == ["trace-two", "trace-one"]
