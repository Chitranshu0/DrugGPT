from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph import graph
from retriever import VectorDatabaseNotReadyError, ensure_database_ready
from vector_db import get_database_status, rebuild_vector_database

app = FastAPI(
    title="DrugGPT",
    version="1.0"
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str


async def generate_response(
    message: str,
    thread_id: str
):

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = graph.invoke(
        {
            "question": message
        },
        config=config
    )

    yield result["answer"]


@app.get("/")
def home():

    return {
        "status": "running"
    }


@app.get("/vector-db/status")
def vector_database_status():
    """Report whether the persistent local Chroma collection is ready for chat."""
    return get_database_status()


@app.post("/vector-db/rebuild")
def rebuild_vector_database_endpoint():
    """Recreate the Chroma collection from all bundled medical PDFs."""
    try:
        result = rebuild_vector_database()
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Vector database rebuild failed: {error}") from error

    return {"status": "success", **result}


@app.post("/chat")
async def chat(request: ChatRequest):

    try:
        ensure_database_ready()
    except VectorDatabaseNotReadyError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return StreamingResponse(
        generate_response(
            request.message,
            request.thread_id
        ),
        media_type="text/plain"
    )
