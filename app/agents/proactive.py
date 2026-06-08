"""
Proactive Insights Agent — analyzes user account data after a support
interaction and surfaces relevant insights the user didn't ask about.
Turns reactive support into proactive service.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.tools.user_db import (
    get_account_status,
    get_recent_transactions,
    check_transfer_limits,
)


PROACTIVE_PROMPT = """You are a proactive insights specialist for InfinitePay's support team.

PURPOSE: After a support interaction, surface one genuinely useful observation the customer didn't ask about — turning reactive support into proactive service. Only surface insights that are directly relevant to what the customer came for.

Account data: {account_data}
Customer question: {original_question}
Support response: {support_response}

WHEN TO RESPOND "NO_INSIGHT" (return ONLY this word, nothing else):
- The insight topic doesn't match the customer's question (login question → transfers insight is irrelevant)
- The account is suspended, blocked, or the situation is urgent or distressed
- There is nothing specific or genuinely useful to add
- When in doubt

WHEN TO SURFACE AN INSIGHT:
- It must be about the exact same topic the customer asked about
- It must reference specific data: amounts, dates, or statuses
- It must be genuinely useful, not generic ("your account is in good standing" is not an insight)

FORMAT:
- Maximum 2 sentences
- Respond in the same language as the customer question
- Return ONLY the insight or "NO_INSIGHT" — no preamble, no explanation
"""


def generate_insight(
    user_id: str,
    original_question: str,
    support_response: str,
) -> str:
    """
    Generate a proactive insight based on user account data.

    Args:
        user_id: user identifier
        original_question: what the user asked
        support_response: what the support agent already answered

    Returns:
        insight string or empty string if no insight needed
    """
    try:
        # Gather account data
        account_status = get_account_status(user_id)
        transactions = get_recent_transactions(user_id, limit=5)
        limits = check_transfer_limits(user_id)

        account_data = f"""
Account Status:
{account_status}

Recent Transactions:
{transactions}

Transfer Limits:
{limits}
"""

        llm = ChatAnthropic(
            model=os.getenv("GUARDRAIL_MODEL", "claude-haiku-4-5-20251001"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=150,
        )

        response = llm.invoke([
            SystemMessage(content=PROACTIVE_PROMPT.format(
                account_data=account_data,
                original_question=original_question,
                support_response=support_response[:500],
            )),
            HumanMessage(content="Generate one proactive insight or NO_INSIGHT."),
        ])

        insight = response.content.strip()

        if insight == "NO_INSIGHT" or not insight:
            return ""

        return insight

    except Exception as e:
        return ""


if __name__ == "__main__":
    test_cases = [
        {
            "user_id": "client789",
            "question": "What are the fees for Maquininha Smart?",
            "response": "The fees are 0.75% for debit and 2.69% for credit.",
        },
        {
            "user_id": "client789",
            "question": "What were my last transactions?",
            "response": "Here are your recent transactions...",
        },
        {
            "user_id": "user_limit_reached",
            "question": "Why can't I make transfers?",
            "response": "Your daily limit of R$5,000 has been reached.",
        },
    ]

    print("Proactive Insights test:")
    print("=" * 60)
    for case in test_cases:
        insight = generate_insight(
            user_id=case["user_id"],
            original_question=case["question"],
            support_response=case["response"],
        )
        print(f"\nUser: {case['question']}")
        print(f"Insight: {insight if insight else '(no insight generated)'}")