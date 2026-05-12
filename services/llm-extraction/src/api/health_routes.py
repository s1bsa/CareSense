"""Health check API routes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    """
    Return service health status for readiness and liveness checks.

    This endpoint returns a JSON payload indicating that the LLM Extraction API
    is running, along with the service name and version. Use it for load balancers,
    orchestrators, or monitoring.

    **Returns:**
    - **JSONResponse** (200): Contains:
        - **status** (str): Always "healthy" when the service is up.
        - **service** (str): Service name, e.g. "LLM Extraction API".
        - **version** (str): API version, e.g. "1.0.0".
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "LLM Extraction API",
            "version": "1.0.0"
        }
    )