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

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

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
    # The Next.js frontend is a different origin, so browsers send an OPTIONS
    # preflight before JSON requests. Without CORS middleware FastAPI answers 405.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(rag_service.settings.cors_origins),
        allow_origin_regex=rag_service.settings.cors_origin_regex,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=False,
        allow_private_network=True,
    )

    # CORSMiddleware answers rejected preflights itself (400), so log the details
    # here from the outer middleware layer to make the cause visible in the terminal.
    @app.middleware("http")
    async def log_rejected_preflights(request: Request, call_next):
        response = await call_next(request)
        if request.method == "OPTIONS" and response.status_code == 400:
            logger.warning(
                "Rejected CORS preflight: origin=%s method=%s headers=%s private_network=%s",
                request.headers.get("origin"),
                request.headers.get("access-control-request-method"),
                request.headers.get("access-control-request-headers"),
                request.headers.get("access-control-request-private-network"),
            )
        return response

    logger.info("DrugGPT API application constructed (model=%s)", rag_service.settings.llm_model)
    register_exception_handlers(app)
    for make_router in ROUTER_FACTORIES:
        app.include_router(make_router(rag_service))
    return app


app = create_app()
