"""
Web search tool used by the Knowledge Agent for general questions
outside the InfinitePay knowledge base.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from tavily import TavilyClient


def search_web(query: str) -> str:
    """
    Search the web for current information.

    Args:
        query: search query string

    Returns:
        formatted string of search results
    """
    try:
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(
            query=query,
            max_results=3,
            search_depth="basic",
        )

        if not response.get("results"):
            return "No web search results found."

        formatted = []
        for i, result in enumerate(response["results"], 1):
            formatted.append(
                f"[Result {i}: {result.get('url', 'unknown')}]\n"
                f"Title: {result.get('title', '')}\n"
                f"{result.get('content', '')}"
            )

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {str(e)}"


if __name__ == "__main__":
    test_queries = [
        "Quando foi o último jogo do Palmeiras?",
        "Principais noticias de Sao Paulo hoje",
    ]
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        result = search_web(query)
        print(result[:500])
        print("...")