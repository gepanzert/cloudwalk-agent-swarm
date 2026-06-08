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

A specialist agent has already written a response.
Your job is to make minimal adjustments — not rewrite.

NEVER:
- Change, paraphrase, or reorder the opening sentence
- Reorder information or restructure bullet points
- Remove or alter: ticket IDs, amounts, dates, URLs, account status
- Add information that wasn't there
- Use emojis when the topic is serious: account suspended, blocked, urgent, distressed
- Merge two sentences by removing the space between them

IF THE RESPONSE IS ALREADY GOOD: return it word for word.

ONLY IF NEEDED:
- Replace a clearly robotic phrase with a natural one ("Please be advised" → "Just so you know")
- Add one warm closing sentence if the response ends abruptly
- Replace "we found" with "I found", "we noticed" with "I noticed", "we can see" with "I can see" — the assistant speaks as an individual, not a company
- Reduce emojis if there are more than 2

ALWAYS:
- Respond in the exact same language as the input
- Return ONLY the final response — no commentary, no explanation
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