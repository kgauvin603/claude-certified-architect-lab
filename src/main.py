from fastapi import FastAPI
from pydantic import BaseModel
from src.agent.coordinator import process_request

app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    request_text: str


@app.post("/chat")
async def chat(req: ChatRequest):
    return await process_request(req.session_id, req.user_id, req.request_text)
