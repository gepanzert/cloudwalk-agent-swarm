from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    user_id: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    user_id: str
    agent_used: str = "none"
    thread_id: Optional[str] = None
    sentiment: Optional[str] = None
    priority: Optional[str] = None
    escalated: Optional[bool] = None