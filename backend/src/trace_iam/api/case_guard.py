from fastapi import HTTPException

from trace_iam.domain import Investigation, InvestigationStatus, ScenarioType
from trace_iam.persistence import InvestigationRepository


def require_matching_case(
    investigation_id: str,
    title: str,
    scenario_type: ScenarioType,
    repository: InvestigationRepository,
) -> Investigation | None:
    existing = repository.get_investigation(investigation_id)
    if existing is None:
        return None
    if existing.scenario_type is not scenario_type:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Investigation belongs to {existing.scenario_type.value}; "
                f"create or select a {scenario_type.value} investigation"
            ),
        )
    if existing.title != title:
        raise HTTPException(
            status_code=409,
            detail="Investigation title does not match the persisted case",
        )
    if existing.status is InvestigationStatus.ARCHIVED:
        raise HTTPException(
            status_code=409,
            detail="Archived investigations must be reopened before analysis",
        )
    return existing
