from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    product: str
    version: str


app = FastAPI(title="TRACE IAM Evidence API", version="0.1.0")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        product="TRACE IAM Evidence",
        version=app.version,
    )
