"""
Knowledge Agent — answers questions about InfinitePay products/services
using RAG over the company website, with web search fallback for
general questions.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.tools.rag import search_knowledge_base
from app.tools.web_search import search_web


# ── LangChain tools (wraps our functions so Claude can call them) ─────────────

@tool
def infinitepay_knowledge_base(query: str) -> str:
    """
    Search InfinitePay's internal knowledge base for information about
    products, services, fees, features, and how-to guides.
    Use this FIRST for any question about InfinitePay.
    """
    return search_knowledge_base(query)


@tool
def general_web_search(query: str) -> str:
    """
    Search the web for general information not related to InfinitePay.
    Use this for news, sports, general knowledge questions, or anything
    outside InfinitePay's products and services.
    """
    return search_web(query)


# ── System prompt ─────────────────────────────────────────────────────────────

KNOWLEDGE_AGENT_PROMPT = """You are a product knowledge specialist for InfinitePay, a Brazilian fintech.

PURPOSE: Answer questions about InfinitePay's products and services using the knowledge base, and handle general off-topic queries via web search. The goal is to be genuinely helpful — either resolving the question directly or redirecting clearly.

LANGUAGE:
- Respond in the exact same language the user wrote in
- English question → English response, even if the source data is in Portuguese
- Translate ALL content to English including table headers and values: Grátis → Free, Débito → Debit, Crédito → Credit, Faturamento Mensal → Monthly Revenue, Acima de → Above, Até → Up to, Todos os níveis → All tiers, Na hora → Instantly, Dia útil → Business day, Recebimento → Payment timing
- Na hora → Instantly (do NOT include the Portuguese in parentheses)
- 1 dia útil → 1 business day (do NOT include the Portuguese in parentheses)
- Portuguese question → Portuguese response
- Unidentifiable language (morse, binary, base64) → Portuguese
- Never mix languages in the same response

TOOLS:
- InfinitePay questions → infinitepay_knowledge_base first
- General questions (news, sports, weather) → general_web_search

RESPONSE RULES:
- Be concise, specific, and conversational — short sentences and bullet points
- Never invent fees, rates, or product features
- If the knowledge base lacks information, say so honestly
- Do NOT cite sources for InfinitePay content — it comes from InfinitePay's own website
- Always show fees tiered by monthly revenue (faturamento) — never show only the lowest tier
- End with one relevant follow-up offer when appropriate

WEB SEARCH — real-time queries only:
- Open with: "The most recent result I found was from [DATE] — for current information check directly:"
- Cite the source URL and date
- Never present real-time information as current fact
- Close with: "For up-to-date information, check [source] directly. Is there anything InfinitePay-related I can help with?"
"""


# ── Agent ─────────────────────────────────────────────────────────────────────

def run_knowledge_agent(message: str, user_id: str = "unknown", history: list = None, model: str = None) -> str:
    llm = ChatAnthropic(
        model=model or os.getenv("KNOWLEDGE_MODEL", "claude-sonnet-4-6"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
    )

    tools = [infinitepay_knowledge_base, general_web_search]
    llm_with_tools = llm.bind_tools(tools)

    # build messages with history if available
    messages = [SystemMessage(content=KNOWLEDGE_AGENT_PROMPT)]

    # add previous turns so the agent has context
    if history:
        messages.extend(history[:-1])  # all but the last (which is the current message)

    messages.append(HumanMessage(content=message))

    for _ in range(5):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == "infinitepay_knowledge_base":
                result = infinitepay_knowledge_base.invoke(tool_args)
            elif tool_name == "general_web_search":
                result = general_web_search.invoke(tool_args)
            else:
                result = f"Unknown tool: {tool_name}"

            from langchain_core.messages import ToolMessage
            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )

    return "I was unable to find a complete answer. Please try rephrasing your question."


if __name__ == "__main__":
    test_cases = [
        ("What are the fees of the Maquininha Smart?", "client789"),
        ("Como usar meu celular como maquininha?", "client789"),
        ("Quando foi o último jogo do Palmeiras?", "client789"),
    ]

    for message, user_id in test_cases:
        print(f"\n{'='*60}")
        print(f"User: {message}")
        print(f"{'='*60}")
        response = run_knowledge_agent(message, user_id)
        print(f"Agent: {response}")