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

Your responsibilities:
- Help users with account issues, transaction problems, login difficulties, and transfer failures
- Always look up the user's actual account data before responding
- Use the available tools to get real information about the user's account
- Always respond in the same language the user writes in (Portuguese or English)
- Be empathetic, clear, and solution-focused

Tool usage guidelines:
- For login issues → use tool_get_login_status
- For transfer failures → use tool_check_transfer_limits and tool_get_recent_transactions
- For general account questions → use tool_get_account_status
- For unresolvable issues → use tool_create_support_ticket to escalate

Important rules:
- Always identify yourself as InfinitePay support
- Never make up account information — only use data from the tools
- If you cannot resolve the issue, create a support ticket
- Be specific about what you found in the user's account
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


def run_support_agent(message: str, user_id: str) -> str:
    """
    Run the Support Agent on a user message.

    Args:
        message: user's support request
        user_id: user identifier (used to look up account data)

    Returns:
        agent's response as a string
    """
    llm = ChatAnthropic(
        model=os.getenv("SUPPORT_MODEL", "claude-sonnet-4-6"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
    )

    llm_with_tools = llm.bind_tools(TOOLS)

    messages = [
        SystemMessage(content=SUPPORT_AGENT_PROMPT),
        HumanMessage(content=f"User ID: {user_id}\nMessage: {message}"),
    ]

    for _ in range(5):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_fn = TOOL_MAP.get(tool_name)

            if tool_fn:
                result = tool_fn.invoke(tool_call["args"])
            else:
                result = f"Unknown tool: {tool_name}"

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