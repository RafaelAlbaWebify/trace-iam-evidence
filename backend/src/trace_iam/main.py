from fastapi import FastAPI
from pydantic import BaseModel

from trace_iam.api import (
    guest_b2b_router,
    investigation_router,
    resource_assignment_router,
)


class HealthResponse(BaseModel):
    status: str
    product: str
    version: str


app = FastAPI(title="TRACE IAM Evidence API", version="0.1.0")
app.include_router(investigation_router)
app.include_router(resource_assignment_router)
app.include_router(guest_b2b_router)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        product="TRACE IAM Evidence",
        version=app.version,
    )
