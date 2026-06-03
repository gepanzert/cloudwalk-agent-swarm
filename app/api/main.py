from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import uuid

load_dotenv()

from app.api.schemas import ChatRequest, ChatResponse
from app.graph.build_graph import get_graph
from app.guardrails import check_input, check_output

app = FastAPI(
    title="CloudWalk Agent Swarm",
    description="Multi-agent system for InfinitePay customer support",
    version="0.1.0",
)

# CORS — allows frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
        "https://*.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        input_check = check_input(request.message)
        if not input_check["allowed"]:
            return ChatResponse(
                response="I'm sorry, I'm not able to help with that request. "
                         "Please ask me about InfinitePay products or services.",
                user_id=request.user_id,
                agent_used="guardrail_blocked",
                thread_id=request.thread_id,
            )

        thread_id = request.thread_id or str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        graph = get_graph()
        result = graph.invoke(
            {
                "messages": [HumanMessage(content=request.message)],
                "user_id": request.user_id,
                "agent_used": "",
                "final_response": "",
                "escalate": False,
                "sentiment": "normal",
                "priority": "low",
            },
            config=config,
        )

        final_response = result["final_response"]

        output_check = check_output(final_response)
        if not output_check["passed"]:
            return ChatResponse(
                response="I apologize, but I'm unable to provide that response. "
                         "Please try rephrasing your question.",
                user_id=request.user_id,
                agent_used="guardrail_blocked",
                thread_id=thread_id,
            )

        return ChatResponse(
            response=final_response,
            user_id=request.user_id,
            agent_used=result.get("agent_used", "unknown"),
            thread_id=thread_id,
            sentiment=result.get("sentiment"),
            priority=result.get("priority"),
            escalated=result.get("escalate", False),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))