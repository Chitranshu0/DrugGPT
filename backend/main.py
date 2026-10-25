"""FastAPI entry point for the DrugGPT backend.

Run from the project root:

    uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend import __version__
from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.api.routes.models import router as models_router
from backend.api.routes.threads import router as threads_router
from backend.core.config import SQLITE_CHECKPOINT_DB
from backend.memory.db import ensure_data_dir, init_app_db
from backend.rag.graph import create_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open SQLite and build the graph once when the server starts."""
    ensure_data_dir()
    await init_app_db()

    async with AsyncSqliteSaver.from_conn_string(
        str(SQLITE_CHECKPOINT_DB)
    ) as checkpointer:
        await checkpointer.setup()

        app.state.checkpointer = checkpointer
        app.state.graph = create_graph(checkpointer=checkpointer)

        yield


app = FastAPI(title="DrugGPT", version=__version__, lifespan=lifespan)

app.include_router(health_router)
app.include_router(models_router)
app.include_router(threads_router)
app.include_router(chat_router)


@app.get("/")
def home():
    return {"status": "running"}
