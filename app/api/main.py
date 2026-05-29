from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from app.api.schemas import ChatRequest, ChatResponse
from app.graph.build_graph import get_graph

app = FastAPI(
    title="CloudWalk Agent Swarm",
    description="Multi-agent system for InfinitePay customer support",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "cloudwalk-agent-swarm"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        graph = get_graph()

        result = graph.invoke({
            "messages": [HumanMessage(content=request.message)],
            "user_id": request.user_id,
            "agent_used": "",
            "final_response": "",
            "escalate": False,
        })

        return ChatResponse(
            response=result["final_response"],
            user_id=request.user_id,
            agent_used=result.get("agent_used", "unknown"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))