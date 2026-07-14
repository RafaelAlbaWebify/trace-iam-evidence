from dataclasses import dataclass
from datetime import datetime

from trace_iam.domain import CasePriority, InvestigationStatus, ScenarioType
from trace_iam.persistence.repository import InvestigationSummary


@dataclass(frozen=True, slots=True)
class OperationalCase:
    investigation_id: str
    title: str
    scenario_type: str
    status: str
    priority: str
    external_reference: str | None
    summary: str | None
    created_at: datetime
    archived_at: datetime | None
    last_activity_at: datetime
    analysis_run_count: int


@dataclass(frozen=True, slots=True)
class OperationalDashboard:
    total_cases: int
    active_cases: int
    waiting_for_evidence: int
    ready_for_analysis: int
    under_review: int
    critical_active: int
    archived_cases: int
    filtered_case_count: int
    cases: tuple[OperationalCase, ...]


def build_operational_dashboard(
    summaries: tuple[InvestigationSummary, ...],
    *,
    latest_activity: dict[str, datetime],
    query: str | None = None,
    status: InvestigationStatus | None = None,
    scenario: ScenarioType | None = None,
    priority: CasePriority | None = None,
    include_archived: bool = False,
) -> OperationalDashboard:
    all_cases = tuple(
        OperationalCase(
            investigation_id=item.investigation_id,
            title=item.title,
            scenario_type=item.scenario_type,
            status=item.status.value,
            priority=item.priority.value,
            external_reference=item.external_reference,
            summary=item.summary,
            created_at=item.created_at,
            archived_at=item.archived_at,
            last_activity_at=latest_activity.get(item.investigation_id, item.created_at),
            analysis_run_count=item.analysis_run_count,
        )
        for item in summaries
    )
    normalized_query = query.strip().casefold() if query else ""

    def matches(item: OperationalCase) -> bool:
        if not include_archived and item.status == InvestigationStatus.ARCHIVED.value:
            return False
        if status is not None and item.status != status.value:
            return False
        if scenario is not None and item.scenario_type != scenario.value:
            return False
        if priority is not None and item.priority != priority.value:
            return False
        if normalized_query:
            haystack = " ".join(
                value for value in (
                    item.investigation_id,
                    item.title,
                    item.external_reference or "",
                    item.summary or "",
                )
            ).casefold()
            if normalized_query not in haystack:
                return False
        return True

    filtered = tuple(
        sorted(
            (item for item in all_cases if matches(item)),
            key=lambda item: (item.last_activity_at, item.investigation_id),
            reverse=True,
        )
    )
    active = tuple(item for item in all_cases if item.status != InvestigationStatus.ARCHIVED.value)
    return OperationalDashboard(
        total_cases=len(all_cases),
        active_cases=len(active),
        waiting_for_evidence=sum(
            item.status == InvestigationStatus.DRAFT.value for item in active
        ),
        ready_for_analysis=sum(
            item.status == InvestigationStatus.EVIDENCE_VALIDATED.value for item in active
        ),
        under_review=sum(
            item.status in {InvestigationStatus.ANALYZED.value, InvestigationStatus.REVIEWED.value}
            for item in active
        ),
        critical_active=sum(item.priority == CasePriority.CRITICAL.value for item in active),
        archived_cases=sum(item.status == InvestigationStatus.ARCHIVED.value for item in all_cases),
        filtered_case_count=len(filtered),
        cases=filtered,
    )
