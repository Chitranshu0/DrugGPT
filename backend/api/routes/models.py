"""OpenAI-compatible model listing.

Some clients call GET /v1/models before sending chat requests.
We return the single model this server uses, in OpenAI's response shape.
"""

from fastapi import APIRouter

from backend.api.schemas import ModelInfo, ModelListResponse
from backend.core.config import LLM_MODEL

router = APIRouter(tags=["models"])


@router.get("/v1/models", response_model=ModelListResponse)
def list_models() -> ModelListResponse:
    """Return the configured model in OpenAI-compatible format."""
    return ModelListResponse(
        data=[ModelInfo(id=LLM_MODEL, owned_by="groq")],
    )
