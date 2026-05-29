"""
LangGraph supervisor graph with memory — wires all agents together.
Uses MemorySaver checkpointer for conversation persistence.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.state import AgentState
from app.agents.router import run_router
from app.agents.knowledge import run_knowledge_agent
from app.agents.support import run_support_agent
from app.agents.handoff import run_handoff_agent


# ── Node functions ────────────────────────────────────────────────────────────

def router_node(state: AgentState) -> AgentState:
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
    decision = run_router(last_message)
    return {**state, "agent_used": decision}


def knowledge_node(state: AgentState) -> AgentState:
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
    response = run_knowledge_agent(
        message=last_message,
        user_id=state.get("user_id", "unknown"),
        history=state["messages"],
    )
    return {
        **state,
        "final_response": response,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def support_node(state: AgentState) -> AgentState:
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
    response = run_support_agent(
        message=last_message,
        user_id=state.get("user_id", "unknown"),
        history=state["messages"],
    )
    return {
        **state,
        "final_response": response,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def handoff_node(state: AgentState) -> AgentState:
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
    response = run_handoff_agent(
        message=last_message,
        user_id=state.get("user_id", "unknown"),
    )
    return {
        **state,
        "final_response": response,
        "escalate": True,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


# ── Routing logic ─────────────────────────────────────────────────────────────

def route_after_router(state: AgentState) -> str:
    agent = state.get("agent_used", "knowledge")
    if agent == "support":
        return "support"
    elif agent == "handoff":
        return "handoff"
    else:
        return "knowledge"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("support", support_node)
    graph.add_node("handoff", handoff_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "knowledge": "knowledge",
            "support": "support",
            "handoff": "handoff",
        }
    )

    graph.add_edge("knowledge", END)
    graph.add_edge("support", END)
    graph.add_edge("handoff", END)

    # MemorySaver keeps conversation history in memory
    # In production, replace with SqliteSaver for persistence across restarts
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ── Singleton ─────────────────────────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    graph = build_graph()

    # Test multi-turn conversation — same thread_id = same memory
    config = {"configurable": {"thread_id": "test-thread-1"}}

    turns = [
        ("What are the fees of the Maquininha Smart?", "client789"),
        ("And what about the Tap to Pay fees?", "client789"),
        ("Which one is cheaper?", "client789"),
    ]

    for message, user_id in turns:
        print(f"\n{'='*60}")
        print(f"User: {message}")
        print(f"{'='*60}")

        result = graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "agent_used": "",
                "final_response": "",
                "escalate": False,
            },
            config=config,
        )

        print(f"Agent: {result['agent_used'].upper()}")
        print(f"Response: {result['final_response'][:300]}...")