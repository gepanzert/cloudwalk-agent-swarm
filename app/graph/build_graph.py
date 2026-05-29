"""
LangGraph supervisor graph — wires all agents together.
The router decides which agent handles each message.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.state import AgentState
from app.agents.router import run_router
from app.agents.knowledge import run_knowledge_agent
from app.agents.support import run_support_agent
from app.agents.handoff import run_handoff_agent


# ── Node functions ────────────────────────────────────────────────────────────

def router_node(state: AgentState) -> AgentState:
    """Classify the user's message and decide which agent handles it."""
    # Get the last human message
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    decision = run_router(last_message)

    return {
        **state,
        "agent_used": decision,
    }


def knowledge_node(state: AgentState) -> AgentState:
    """Run the Knowledge Agent and store the response."""
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    response = run_knowledge_agent(
        message=last_message,
        user_id=state.get("user_id", "unknown"),
    )

    return {
        **state,
        "final_response": response,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def support_node(state: AgentState) -> AgentState:
    """Run the Support Agent and store the response."""
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    response = run_support_agent(
        message=last_message,
        user_id=state.get("user_id", "unknown"),
    )

    return {
        **state,
        "final_response": response,
        "messages": state["messages"] + [AIMessage(content=response)],
    }


def handoff_node(state: AgentState) -> AgentState:
    """Escalate to human agent."""
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
    """Conditional edge — sends to the right agent after routing."""
    agent = state.get("agent_used", "knowledge")

    if agent == "support":
        return "support"
    elif agent == "handoff":
        return "handoff"
    else:
        return "knowledge"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph():
    """Construct and compile the agent swarm graph."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("support", support_node)
    graph.add_node("handoff", handoff_node)

    # Entry point
    graph.set_entry_point("router")

    # Conditional routing after the router
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "knowledge": "knowledge",
            "support": "support",
            "handoff": "handoff",
        }
    )

    # All agent nodes end the graph
    graph.add_edge("knowledge", END)
    graph.add_edge("support", END)
    graph.add_edge("handoff", END)

    return graph.compile()


# ── Singleton ─────────────────────────────────────────────────────────────────

_graph = None


def get_graph():
    """Return the compiled graph, building it once."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    graph = build_graph()

    test_cases = [
        ("What are the fees of the Maquininha Smart?", "client789"),
        ("Why am I not able to make transfers?", "user_limit_reached"),
        ("I can't sign in to my account.", "user_login_issue"),
        ("Quando foi o último jogo do Palmeiras?", "client789"),
    ]

    for message, user_id in test_cases:
        print(f"\n{'='*60}")
        print(f"User ({user_id}): {message}")
        print(f"{'='*60}")

        result = graph.invoke({
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "agent_used": "",
            "final_response": "",
            "escalate": False,
        })

        print(f"Routed to: {result['agent_used'].upper()}")
        print(f"Response: {result['final_response'][:300]}...")