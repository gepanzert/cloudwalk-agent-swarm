"""
Router Agent — classifies user intent AND query complexity
to enable dynamic model selection downstream.
Uses claude-haiku for speed and cost efficiency.
"""
import os
import re
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


ROUTER_PROMPT = """You are a router for InfinitePay's customer support system.
Classify the message by BOTH intent and complexity. Respond with exactly one of these four options:

- "knowledge_simple" → single factual question answerable with one RAG lookup
  Examples: fees, product features, how a product works, general questions (news, sports, weather)
- "knowledge_complex" → requires reasoning across multiple concepts or comparison
  Examples: "which product is best for my business", "compare Pix vs link de pagamento for my use case"
- "support_simple" → account query requiring one tool call with a direct answer
  Examples: "what were my last transactions", "what is my transfer limit"
- "support_complex" → requires multiple tools or conditional reasoning
  Examples: "why can't I transfer", "I can't sign in", "my payment was declined", "my account is blocked"

If the message is unclear or nonsensical, default to: knowledge_simple

Examples:
- "What are the fees for Maquininha Smart?" → knowledge_simple
- "Which is better for my food truck, Maquininha Smart or InfiniteTap?" → knowledge_complex
- "What were my last transactions?" → support_simple
- "Why can't I make transfers?" → support_complex
- "I can't sign in to my account" → support_complex
- "Quando foi o último jogo do Palmeiras?" → knowledge_simple
- "bla bla codigo errado" → knowledge_simple

Respond with ONLY one of the four options. No punctuation. No explanation.
"""


def run_router(message: str) -> str:
    """
    Classify a user message by intent and complexity.

    Returns:
        "knowledge_simple", "knowledge_complex", "support_simple", or "support_complex"
    """
    llm = ChatAnthropic(
        model=os.getenv("ROUTER_MODEL", "claude-haiku-4-5-20251001"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=20,
    )
    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=message),
    ])

    result = response.content.strip().lower()
    result = re.sub(r'[^a-z_]', '', result)

    valid = ["knowledge_simple", "knowledge_complex", "support_simple", "support_complex"]
    if result not in valid:
        return "knowledge_simple"
    return result


if __name__ == "__main__":
    test_cases = [
        ("What are the fees of the Maquininha Smart?", "knowledge_simple"),
        ("Which product is better for a food truck?", "knowledge_complex"),
        ("What were my last transactions?", "support_simple"),
        ("Why am I not able to make transfers?", "support_complex"),
        ("I can't sign in to my account.", "support_complex"),
        ("Quando foi o último jogo do Palmeiras?", "knowledge_simple"),
        ("bla bla codigo errado nao sei oq to falando", "knowledge_simple"),
    ]

    print("Router classification test:")
    print("=" * 60)
    correct = 0
    for message, expected in test_cases:
        result = run_router(message)
        status = "✅" if result == expected else "❌"
        if result == expected:
            correct += 1
        print(f"{status} [{result:20}] {message}")
    print(f"\n{correct}/{len(test_cases)} correct")
