from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph import graph

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


@app.post("/chat")
async def chat(request: ChatRequest):

    return StreamingResponse(
        generate_response(
            request.message,
            request.thread_id
        ),
        media_type="text/plain"
    )