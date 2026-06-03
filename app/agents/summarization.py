"""
Summarization Agent — generates a structured summary of a conversation
before escalating to a human agent. Gives human agents instant context.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


SUMMARIZATION_PROMPT = """You are a summarization specialist for InfinitePay's customer support team.

Your job is to create a concise, structured summary of a customer conversation
that will be read by a human support agent who needs to take over the case.

Write a summary with exactly these sections:

**Problem:** One sentence describing what the customer's issue is.
**What was tried:** What the AI agent attempted or found (tools used, data checked).
**Current status:** Where things stand right now.
**Urgency reason:** Why this was escalated to a human.
**Recommended action:** What the human agent should do first.

Rules:
- Maximum 5 sentences total
- Be specific — include amounts, dates, error messages if mentioned
- Write in English regardless of the conversation language
- Focus on facts, not emotions
"""


def generate_summary(messages: list, sentiment: str = "normal") -> str:
    """
    Generate a structured conversation summary for human handoff.

    Args:
        messages: full conversation history
        sentiment: detected sentiment level

    Returns:
        structured summary string
    """
    if not messages:
        return "No conversation history available."

    try:
        # Format conversation for summarization
        conversation_text = []
        for msg in messages:
            role = "Customer" if isinstance(msg, HumanMessage) else "Agent"
            content = msg.content[:500] if hasattr(msg, 'content') else str(msg)[:500]
            conversation_text.append(f"{role}: {content}")

        conversation_str = "\n".join(conversation_text[-10:])  # Last 10 messages

        llm = ChatAnthropic(
            model=os.getenv("GUARDRAIL_MODEL", "claude-haiku-4-5-20251001"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=300,
        )

        response = llm.invoke([
            SystemMessage(content=SUMMARIZATION_PROMPT),
            HumanMessage(content=f"Sentiment level: {sentiment}\n\nConversation:\n{conversation_str}"),
        ])

        return response.content.strip()

    except Exception as e:
        return f"Summary unavailable: {str(e)}"


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage, AIMessage

    test_conversation = [
        HumanMessage(content="I can't process any sales, my business is losing money RIGHT NOW"),
        AIMessage(content="I can see this is directly impacting your business. Let me check your account."),
        HumanMessage(content="I've been trying for 2 hours and nothing works"),
        AIMessage(content="I found that your daily transfer limit has been reached: R$5,000 used of R$5,000."),
    ]

    summary = generate_summary(test_conversation, sentiment="urgent")
    print("Generated summary:")
    print("=" * 60)
    print(summary)