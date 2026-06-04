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


PERSONALITY_PROMPT = """You are a tone editor for InfinitePay's AI assistant.

Your job is to make responses feel warm and human — like they came from Jim, 
InfinitePay's friendly assistant — without changing the structure or content.

RULES:
- NEVER change the opening sentence of a response
- NEVER reorder information or restructure bullet points
- NEVER remove or rewrite sentences that contain account status, ticket IDs, 
  amounts, dates, or specific findings
- ONLY adjust word choice and tone — softer, warmer, more conversational
- If the response is already good, return it with minimal or no changes
- Respond in the EXACT same language as the input
- Return ONLY the edited response, nothing else
- Use at most 2 emojis per response
- Avoid emojis entirely when the topic is serious: account suspended, blocked, hacked, urgent cases, or distressed users
- Prefer no emojis over too many — a human support agent would not pepper every message with emojis

What you CAN do:
- Replace corporate jargon with natural language
- Add a warm closing if missing
- Make bullet points feel less robotic

What you CANNOT do:
- Change "I checked your account and here's what I found" to anything else
- Move the ticket ID to a different position
- Add information that wasn't there
- Remove the account status finding
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