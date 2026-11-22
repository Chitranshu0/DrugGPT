"""Application-wide HTTP error handling."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("druggpt.api")


def register_exception_handlers(app: FastAPI) -> None:
    """Turn unexpected errors into clean JSON 500s instead of raw tracebacks."""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the root cause in the summary line; logger.exception keeps the traceback.
        logger.exception(
            "Request failed: %s %s raised %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check the server logs for details."},
        )
