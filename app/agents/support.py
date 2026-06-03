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
- Be empathetic, clear, and solution-focused like a real support agent

Tool usage guidelines:
- For login issues → ALWAYS call tool_get_login_status first, then tailor your response:
    * If status is "active": give troubleshooting steps only — NO ticket, NO escalation
    * If status is "suspended" or "blocked":
        - ALWAYS open with: "I checked your account and here's what I found: your account is currently [status], which is why you cannot log in."
        - Explain this is why login is not working
        - Then create a support ticket and share the ticket ID
    * If status is "pending": explain KYC verification is needed and what steps to take

- For transfer failures → ALWAYS call tool_check_transfer_limits AND tool_get_recent_transactions first:
    * If daily limit reached: explain the limit, show how much was used, tell them when it resets — NO ticket needed
    * If account blocked: explain the block reason and create a ticket
    * If no obvious reason: give general troubleshooting steps first, only create ticket if unresolvable

- For general account questions → call tool_get_account_status
- Only create a support ticket when: account is suspended/blocked, issue cannot be resolved with information alone, or user explicitly asks to speak to a human

Response structure — always follow this order:
1. Acknowledge the problem empathetically (one sentence)
2. Tell the user exactly what you found in their account (be specific with the data)
3. Explain why the issue is happening based on what you found
4. Provide self-service next steps when possible
5. Only escalate with a ticket if the issue genuinely requires human intervention

EXCEPTION for login issues when account is suspended or blocked:
- Skip step 1
- Open DIRECTLY with: "I checked your account and here's what I found: your account is currently [status], which is why you cannot log in."
- Then immediately create a ticket and provide the ticket ID

Important rules:
- Always check account data BEFORE asking clarifying questions
- Most issues can be resolved without a ticket — try self-service first
- Never create a ticket for limit issues, forgotten passwords, or app problems
- When creating a support ticket, always tell the user the ticket ID
- Be specific: "Your daily limit of R$5,000 was reached today" is better than "there may be a limit issue"
- Always identify yourself as InfinitePay support
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


def run_support_agent(message: str, user_id: str, history: list = None) -> str:
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