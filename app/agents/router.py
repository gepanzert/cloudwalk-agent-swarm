"""
Router Agent — the supervisor that decides which agent handles each message.
Uses claude-haiku for speed and cost efficiency.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


ROUTER_PROMPT = """You are a router for InfinitePay's customer support system.
Your ONLY job is to classify the user's message and respond with exactly one word.
Classification rules:
- "knowledge" → questions about InfinitePay products, services, fees, features, how-to guides, or general questions (news, sports, weather, etc.)
- "support" → account issues, login problems, transfer failures, transaction disputes, anything requiring the user's account data
- If the message is unclear, nonsensical, or cannot be classified, default to: knowledge

Examples:
- "What are the fees for Maquininha Smart?" → knowledge
- "How do I use Tap to Pay?" → knowledge
- "Quando foi o último jogo do Palmeiras?" → knowledge
- "Why can't I make transfers?" → support
- "I can't sign in to my account" → support
- "What were my last transactions?" → support
- "My payment was declined" → support
- "bla bla codigo errado nao sei oq to falando" → knowledge
- "asdfghjkl" → knowledge

Respond with ONLY the single word: knowledge OR support
No punctuation. No explanation. Just the word.
"""


def run_router(message: str) -> str:
    """
    Classify a user message and return the target agent.

    Args:
        message: the user's message

    Returns:
        "knowledge" or "support"
    """
    llm = ChatAnthropic(
        model=os.getenv("ROUTER_MODEL", "claude-haiku-4-5-20251001"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=10,  # We only need one word back
    )


    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=message),
    ])

    import re
    result = re.sub(r'[^a-z]', '', response.content.strip().lower())

    if result not in ["knowledge", "support"]:
        return "knowledge"
    return result


if __name__ == "__main__":
    test_cases = [
        "What are the fees of the Maquininha Smart?",
        "Como usar meu celular como maquininha?",
        "Quando foi o último jogo do Palmeiras?",
        "Why am I not able to make transfers?",
        "I can't sign in to my account.",
        "What were my last transactions?",
        "Quais as principais notícias de São Paulo hoje?",
    ]

    print("Router classification test:")
    print("=" * 50)
    for message in test_cases:
        decision = run_router(message)
        print(f"[{decision.upper():10}] {message}")