"""DrugGPT FastAPI backend entrypoint.

Run:
    python main.py              # start the FastAPI backend (:8000)
    uvicorn main:app            # alternative (exposes lazy ``app``)
    python main.py --reload     # with auto-reload
    python main.py --port 9000  # custom port
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn  # noqa: E402


def _load_app():
    """Lazily create the FastAPI app so ``--help`` stays fast.

    The app factory imports heavy ML dependencies (sentence-transformers,
    langchain, …) that are unnecessary for argument parsing.
    """
    from src.api.app import create_app  # noqa: PLC0415

    return create_app()


def __getattr__(name: str):
    """PEP 562: expose a lazy ``app`` attribute for ``uvicorn main:app``."""
    if name == "app":
        return _load_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def main() -> None:
    from src.core.config import settings  # noqa: PLC0415

    parser = argparse.ArgumentParser(prog="main", description="DrugGPT FastAPI backend")
    parser.add_argument("--host", default=settings.api_host, help="Bind host")
    parser.add_argument("--port", type=int, default=settings.api_port, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
