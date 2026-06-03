"""
Shared state for the LangGraph agent swarm.
Every node reads from and writes to this state object.
"""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Full conversation history — add_messages appends rather than overwrites
    messages: Annotated[list, add_messages]

    # User identifier passed in from the API
    user_id: str

    # Which agent the router decided to use
    agent_used: str

    # Final response to return to the user
    final_response: str

    # Whether to escalate to a human
    escalate: bool


from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    agent_used: str
    final_response: str
    escalate: bool
    sentiment: str
    priority: str