"""
Sentiment Agent — detects frustration, urgency, or distress
in user messages before routing. Routes to human handoff
when intervention is needed.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


SENTIMENT_PROMPT = """You are a sentiment classifier for InfinitePay's customer support system.

PURPOSE: Detect emotional urgency in customer messages so the system can prioritize and route correctly.
Normal and frustrated cases go through the standard support pipeline.
Urgent and distressed cases are short-circuited to a human agent immediately.

OUTPUT: Respond with exactly one word — nothing else: normal, frustrated, urgent, or distressed

CLASSIFICATION:
- normal → routine question or support request, no urgency or distress
- frustrated → mild anger, repeated attempts, "nobody helps me", "second time I contact"
- urgent → explicit business impact or time-sensitive financial situation: "can't process sales", "money stuck", "losing money now"
- distressed → strong anger, threats, or significant financial harm: "UNACCEPTABLE", "reporting to Procon", "lost thousands"

RULE: Standard account issues (fees, limits, transfers not working) are NORMAL even if phrased as problems.
Classify as urgent or distressed ONLY when there is explicit business impact, financial loss, or strong emotional language.

EXAMPLES:
- "What are the fees?" → normal
- "Why can't I make transfers?" → normal
- "Transfer is not working" → normal
- "I've been trying to fix this for 3 days and nobody helps" → frustrated
- "This is the second time I contact you about the same problem" → frustrated
- "I can't process any sales right now, my business is losing money" → urgent
- "My account has been frozen and I have R$5000 stuck inside" → urgent
- "This is UNACCEPTABLE. I'm going to report InfinitePay to Procon" → distressed
- "I've lost thousands because of your system failure" → distressed
    """


def analyze_sentiment(message: str) -> dict:
    """
    Analyze the sentiment and urgency of a user message.

    Returns:
        dict with keys:
            - sentiment: "normal" | "frustrated" | "urgent" | "distressed"
            - needs_human: bool (True if frustrated/urgent/distressed)
            - priority: "low" | "medium" | "high" | "critical"
    """
    try:
        llm = ChatAnthropic(
            model=os.getenv("GUARDRAIL_MODEL", "claude-haiku-4-5-20251001"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=10,
        )

        response = llm.invoke([
            SystemMessage(content=SENTIMENT_PROMPT),
            HumanMessage(content=message),
        ])

        sentiment = response.content.strip().lower()

        if sentiment not in ["normal", "frustrated", "urgent", "distressed"]:
            sentiment = "normal"

        priority_map = {
            "normal": "low",
            "frustrated": "medium",
            "urgent": "high",
            "distressed": "critical",
        }

        return {
            "sentiment": sentiment,
            "needs_human": sentiment in ["urgent", "distressed"],
            "priority": priority_map[sentiment],
        }

    except Exception as e:
        return {
            "sentiment": "normal",
            "needs_human": False,
            "priority": "low",
        }


if __name__ == "__main__":
    test_cases = [
        ("What are the fees for Maquininha Smart?", "normal"),
        ("I've been trying to fix this for 3 days", "frustrated"),
        ("I can't process sales, my business is losing money RIGHT NOW", "urgent"),
        ("This is UNACCEPTABLE. I'm reporting you to Procon", "distressed"),
        ("Minha conta está bloqueada e tenho R$5000 presos", "urgent"),
        ("Why can't I make transfers?", "normal"),
    ]

    print("Sentiment analysis test:")
    print("=" * 60)
    for message, expected in test_cases:
        result = analyze_sentiment(message)
        status = "✓" if result["sentiment"] == expected else "~"
        print(f"{status} [{result['sentiment'].upper():12}] [{result['priority'].upper():8}] {message[:50]}")