"""
Personality Agent — post-processes agent responses to ensure
consistent voice, tone, and style across all agents.
Inspired by InfinitePay's Jim assistant personality.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


PERSONALITY_PROMPT = """You are a personality editor for InfinitePay's AI assistant.

Your job is to take a technically correct response and rewrite it with InfinitePay's voice:
- Direct and conversational — short sentences, no corporate jargon
- Warm but professional — like a knowledgeable friend, not a robot
- Brazilian fintech culture — understand the context of small business owners
- Respond in the EXACT same language as the original response (Portuguese or English)
- Keep all factual content, numbers, and data exactly as they are
- Keep markdown formatting (tables, bullets, bold) intact
- Do NOT add new information
- Do NOT remove important details
- Do NOT change ticket IDs, amounts, or specific data
- If the response is already good, return it with minimal changes

The output should feel like it came from Jim — InfinitePay's friendly AI assistant —
not from a generic chatbot.

Return ONLY the rewritten response, nothing else.
"""


def apply_personality(response: str, agent_used: str) -> str:
    """
    Apply InfinitePay's voice and personality to an agent response.

    Args:
        response: the raw response from a specialist agent
        agent_used: which agent generated the response

    Returns:
        response with consistent personality applied
    """
    # Skip personality for guardrail blocks and handoff tickets
    # These need to stay precise and formal
    if agent_used in ["guardrail_blocked", "handoff"]:
        return response
    

    # Skip personality if response starts with account status check 
    # to preserve the critical opening line
    if response.startswith("I checked your account"):
        return response

    # Skip for very short responses
    if len(response) < 50:
        return response

    try:
        llm = ChatAnthropic(
            model=os.getenv("GUARDRAIL_MODEL", "claude-haiku-4-5-20251001"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=2048,
        )

        result = llm.invoke([
            SystemMessage(content=PERSONALITY_PROMPT),
            HumanMessage(content=f"Rewrite this response with InfinitePay's voice:\n\n{response}"),
        ])

        return result.content.strip()

    except Exception as e:
        # Fail open — return original if personality agent fails
        return response


if __name__ == "__main__":
    test_responses = [
        (
            "The daily transfer limit for your account has been reached. "
            "Your limit is R$5,000.00 and you have used R$5,000.00 today. "
            "The limit resets at midnight.",
            "support"
        ),
        (
            "Here are the fees for the Maquininha Smart: Débito 0.75%, Crédito 1x 2.69%.",
            "knowledge"
        ),
    ]

    print("Personality Agent test:")
    print("=" * 60)
    for response, agent in test_responses:
        print(f"\nOriginal ({agent}):\n{response}")
        print(f"\nWith personality:")
        print(apply_personality(response, agent))
        print("-" * 60)