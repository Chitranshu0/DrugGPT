"""uvicorn main:app --reload --host 127.0.0.1 --port 8000

The FastAPI app is exposed lazily through PEP 562 ``__getattr__`` so that
``uvicorn main:app`` never pays the heavy ML-import cost unless an actual
request arrives. There is no ``python main.py`` entrypoint; run uvicorn directly.
"""
from __future__ import annotations

from src.core.config import setup_logging

# Configure logging at import time so `uvicorn main:app --reload` (which never
# calls a ``main()``) still gets consistent, readable project logs.
setup_logging()


def __getattr__(name: str):
    """PEP 562: expose a lazy ``app`` attribute for ``uvicorn main:app``."""
    if name == "app":
        from src.api.app import app  # noqa: PLC0415

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name}")
