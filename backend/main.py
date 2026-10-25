"""FastAPI entry point for the DrugGPT backend.

Run from the project root:

    uvicorn backend.main:app --reload
"""

from fastapi import FastAPI

from backend import __version__
from backend.api.routes.chat import router as chat_router
from backend.api.routes.health import router as health_router
from backend.api.routes.models import router as models_router

app = FastAPI(title="DrugGPT", version=__version__)

app.include_router(health_router)
app.include_router(models_router)
app.include_router(chat_router)


@app.get("/")
def home():
    return {"status": "running"}
