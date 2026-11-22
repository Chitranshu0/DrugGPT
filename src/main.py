"""ASGI entrypoint and composition root for the DrugGPT FastAPI backend.

Runtime shims and logging are configured first, then the API is assembled from
the per-domain route modules listed in ``ROUTER_FACTORIES`` below. Run with
``uvicorn src.main:app --reload``.
"""

from __future__ import annotations

from src.core.runtime import configure_runtime

configure_runtime()

from src.core.config import setup_logging  # noqa: E402

setup_logging()

import logging  # noqa: E402

from fastapi import FastAPI  # noqa: E402

from src.api.errors import register_exception_handlers  # noqa: E402
from src.api.metadata import API_VERSION, DESCRIPTION, TAGS_METADATA  # noqa: E402
from src.api.routes import chat, clinician, index, meta, patients, reviews  # noqa: E402
from src.rag.service import MedicalRAGService  # noqa: E402

logger = logging.getLogger("druggpt.api")

# Add a new view module here; each factory binds the same service into its handlers.
ROUTER_FACTORIES = (
    meta.make_router,
    index.make_router,
    patients.make_router,
    chat.make_router,
    reviews.make_router,
    clinician.make_router,
)


def create_app(service: MedicalRAGService | None = None) -> FastAPI:
    """Build the API. Tests inject a fake service; production uses the real one."""
    rag_service = service or MedicalRAGService()
    app = FastAPI(
        title="DrugGPT API",
        version=API_VERSION,
        description=DESCRIPTION,
        contact={
            "name": "DrugGPT maintainers",
            "url": "https://github.com/",
        },
        license_info={"name": "MIT"},
        terms_of_service="https://github.com/",
        openapi_tags=TAGS_METADATA,
    )
    logger.info("DrugGPT API application constructed (model=%s)", rag_service.settings.llm_model)
    register_exception_handlers(app)
    for make_router in ROUTER_FACTORIES:
        app.include_router(make_router(rag_service))
    return app


app = create_app()
