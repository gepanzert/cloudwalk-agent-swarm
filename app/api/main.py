from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.schemas import ChatRequest, ChatResponse

load_dotenv()

app = FastAPI(
    title="CloudWalk Agent Swarm",
    description="Multi-agent system for InfinitePay customer support",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "cloudwalk-agent-swarm", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Placeholder — Day 4 replaces this with the real agent graph
    return ChatResponse(
        response=f"Echo: {request.message}",
        user_id=request.user_id,
        agent_used="echo",
    )