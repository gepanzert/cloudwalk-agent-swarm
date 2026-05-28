"""
RAG retrieval tool — used by the Knowledge Agent.
Searches the InfinitePay vector store and returns relevant chunks.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_chroma import Chroma
from langchain_voyageai import VoyageAIEmbeddings

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "infinitepay_kb"

_vector_store = None


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        embeddings = VoyageAIEmbeddings(
            model="voyage-3-large",
            voyage_api_key=os.getenv("VOYAGE_API_KEY"),
        )
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PATH,
        )
    return _vector_store


def search_knowledge_base(query: str, k: int = 4) -> str:
    try:
        vector_store = get_vector_store()
        results = vector_store.similarity_search(query, k=k)

        if not results:
            return "No relevant information found in the InfinitePay knowledge base."

        formatted = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "unknown")
            formatted.append(f"[Source {i}: {source}]\n{doc.page_content}")

        return "\n\n---\n\n".join(formatted)

    except Exception as e:
        return f"Knowledge base search failed: {str(e)}"


if __name__ == "__main__":
    test_queries = [
        "What are the fees for Maquininha Smart?",
        "Como funciona o Pix Parcelado?",
        "digital account features",
    ]
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        result = search_knowledge_base(query, k=2)
        print(result[:500])
        print("...")
