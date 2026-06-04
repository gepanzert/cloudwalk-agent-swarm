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


PROACTIVE_PROMPT = """You are a proactive customer success specialist for InfinitePay.

You have just reviewed a customer's account data after they contacted support.
Your job is to identify ONE relevant insight or opportunity that the customer
didn't ask about but would find genuinely useful.

Account data provided:
{account_data}

Original customer question: {original_question}
Support response already given: {support_response}

Rules:
- Identify only ONE insight — the most relevant one
- Only surface an insight if it's genuinely useful (don't force it)
- If there's nothing meaningful to add, respond with exactly: "NO_INSIGHT"
- If the support response involves account suspension, blocking, hacking, or any urgent/distressed situation, respond with exactly: "NO_INSIGHT"
- Never surface insights about unrelated topics when the user is dealing with a serious issue
- Keep it to 2 sentences maximum
- Be specific — mention actual amounts, dates, or statuses from the data
- Frame it as helpful observation, not as a problem
- CRITICAL: Always respond in the same language as the original question
- If the original question is in English, respond in English even if the account data is in Portuguese
- If the original question is in Portuguese, respond in Portuguese
- Translate any Portuguese terms from the account data into English when responding in English

Good insight examples:
- "I also noticed your last Pix transfer of R$50 failed — would you like me to check what happened?"
- "Your account has R$4,800 remaining in daily transfer limit if you need to make more transfers today."
- "I can see you have 3 completed sales today totaling R$1,850 — all processed successfully."

Bad insight examples (too generic, not useful):
- "Let me know if you need anything else."
- "Your account is in good standing."
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