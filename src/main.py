from fastapi import FastAPI
from pydantic import BaseModel

from src.agent.coordinator import process_request


app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    request_text: str


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    return process_request(req.session_id, req.user_id, req.request_text)
