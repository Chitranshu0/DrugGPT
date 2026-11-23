"""Health check endpoints.

Monitoring tools and local scripts can call these to confirm the API is up.
"""

from fastapi import APIRouter

from backend import __version__
from backend.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


def _healthy() -> HealthResponse:
    return HealthResponse(status="ok", service="DrugGPT", version=__version__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return OK when the API is running."""
    return _healthy()


@router.get("/healthz", response_model=HealthResponse, include_in_schema=False)
def healthz() -> HealthResponse:
    """Alias for tools that expect the /healthz name."""
    return _healthy()
