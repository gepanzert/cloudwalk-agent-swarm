"""
Support Agent — handles customer support queries by looking up
real user data and providing personalized assistance.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from app.tools.user_db import (
    get_account_status,
    get_recent_transactions,
    check_transfer_limits,
    get_login_status,
    create_support_ticket,
)


# ── LangChain tools ───────────────────────────────────────────────────────────

@tool
def tool_get_account_status(user_id: str) -> str:
    """Get the account status, KYC verification status, and plan for a user."""
    return get_account_status(user_id)


@tool
def tool_get_recent_transactions(user_id: str) -> str:
    """Get the 5 most recent transactions for a user."""
    return get_recent_transactions(user_id)


@tool
def tool_check_transfer_limits(user_id: str) -> str:
    """Check transfer limits and identify why transfers might be failing."""
    return check_transfer_limits(user_id)


@tool
def tool_get_login_status(user_id: str) -> str:
    """Check if a user can log in and why they might be having login issues."""
    return get_login_status(user_id)


@tool
def tool_create_support_ticket(user_id: str, summary: str) -> str:
    """Create a support ticket when the issue cannot be resolved automatically."""
    return create_support_ticket(user_id, summary)


# ── System prompt ─────────────────────────────────────────────────────────────

SUPPORT_AGENT_PROMPT = """You are a customer support specialist for InfinitePay, a Brazilian fintech.

PURPOSE: Resolve account issues by looking up real user data through tools and giving specific, accurate answers. The goal is to resolve without escalating — only create a ticket when the issue genuinely requires human intervention.

LANGUAGE: Respond in the same language the user writes in. If unidentifiable, use Portuguese.

TOOLS — always call before responding, never guess:
- Login issues → tool_get_login_status
- Transfer issues → tool_check_transfer_limits + tool_get_recent_transactions
- Account questions → tool_get_account_status
- Create a ticket ONLY when: account is suspended/blocked, or user explicitly asks for a human

RESPONSE RULES:
- Explain what you found before giving a solution
- Use actual numbers, statuses, and dates from tool results
- One sentence of acknowledgment is enough — be empathetic but concise
- At most 1 emoji per response. None for serious cases (suspended, blocked, urgent)
- Always identify yourself as InfinitePay support
- NEVER use or invent the user's name — address them as "you" or not at all

CRITICAL — SUSPENDED OR BLOCKED ACCOUNT:
Acknowledge the suspension or block in your opening sentence.
Explain this prevents login.
Create a support ticket and share the ticket ID.

CRITICAL — ACCOUNT NOT FOUND:
If any tool returns "no account found" or "user not found":
Respond ONLY with: "I wasn't able to find an account associated with your information. Please contact InfinitePay support at infinitepay.io/ajuda."
Never invent data. If the user sends a ticket ID (ESC-XXXXX or TKT-XXXXX), ask for their registered email instead.
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

TOOLS = [
    tool_get_account_status,
    tool_get_recent_transactions,
    tool_check_transfer_limits,
    tool_get_login_status,
    tool_create_support_ticket,
]

TOOL_MAP = {t.name: t for t in TOOLS}


def run_support_agent(message: str, user_id: str, history: list = None, model: str = None) -> str:
    """
    Run the Support Agent on a user message.

    Args:
        message: user's support request
        user_id: user identifier (used to look up account data)

    Returns:
        agent's response as a string
    """
    llm = ChatAnthropic(
        model=model or os.getenv("SUPPORT_MODEL", "claude-sonnet-4-6"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
    )
    llm_with_tools = llm.bind_tools(TOOLS)

    messages = [SystemMessage(content=SUPPORT_AGENT_PROMPT)]
    if history:
        messages.extend(history[:-1])
    messages.append(HumanMessage(content=f"User ID: {user_id}\nMessage: {message}"))

    for _ in range(5):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_fn = TOOL_MAP.get(tool_name)
            result = tool_fn.invoke(tool_call["args"]) if tool_fn else f"Unknown tool: {tool_name}"
            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )

    return "I was unable to resolve your issue automatically. Please contact support directly."


if __name__ == "__main__":
    test_cases = [
        ("Why am I not able to make transfers?", "user_limit_reached"),
        ("I can't sign in to my account.", "user_login_issue"),
        ("What were my last transactions?", "client789"),
    ]

    for message, user_id in test_cases:
        print(f"\n{'='*60}")
        print(f"User ({user_id}): {message}")
        print(f"{'='*60}")
        response = run_support_agent(message, user_id)
        print(f"Agent: {response}")