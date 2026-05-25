from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: str


class ChatResponse(BaseModel):
    response: str
    user_id: str
    agent_used: str = "none"