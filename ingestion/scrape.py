"""
RAG Ingestion Pipeline
Scrapes InfinitePay URLs, chunks content, embeds it, stores in ChromaDB.
Run this once before starting the API: python -m ingestion.scrape
"""

import os
import time
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_voyageai import VoyageAIEmbeddings

# ── URLs to scrape ────────────────────────────────────────────────────────────
URLS = [
    "https://www.infinitepay.io",
    "https://www.infinitepay.io/maquininha",
    "https://www.infinitepay.io/maquininha-celular",
    "https://www.infinitepay.io/tap-to-pay",
    "https://www.infinitepay.io/pdv",
    "https://www.infinitepay.io/receba-na-hora",
    "https://www.infinitepay.io/gestao-de-cobranca",
    "https://www.infinitepay.io/gestao-de-cobranca-2",
    "https://www.infinitepay.io/link-de-pagamento",
    "https://www.infinitepay.io/loja-online",
    "https://www.infinitepay.io/boleto",
    "https://www.infinitepay.io/conta-digital",
    "https://www.infinitepay.io/pix",
    "https://www.infinitepay.io/pix-parcelado",
    "https://www.infinitepay.io/emprestimo",
    "https://www.infinitepay.io/cartao",
    "https://www.infinitepay.io/rendimento",
    "https://www.infinitepay.io/conta-pj",
]

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "infinitepay_kb"


def scrape_urls(urls: list[str]) -> list:
    """Scrape all URLs and return list of documents."""
    documents = []
    for url in urls:
        print(f"Scraping: {url}")
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()
            # Tag each chunk with its source URL for citations later
            for doc in docs:
                doc.metadata["source"] = url
            documents.extend(docs)
            time.sleep(1)  # Be polite to the server
        except Exception as e:
            print(f"  ⚠ Failed to scrape {url}: {e}")
            continue
    print(f"\n✓ Scraped {len(documents)} pages successfully")
    return documents


def chunk_documents(documents: list) -> list:
    """Split documents into smaller chunks for better retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # ~1000 characters per chunk
        chunk_overlap=200,    # 200 char overlap so context isn't lost at boundaries
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"✓ Split into {len(chunks)} chunks")
    return chunks


def build_vector_store(chunks: list) -> Chroma:
    """Embed chunks and store in ChromaDB."""
    print("\nEmbedding chunks and building vector store...")
    print("(This takes 2-3 minutes — embedding each chunk via Anthropic API)")

    embeddings = VoyageAIEmbeddings(
        model="voyage-3-large",
        voyage_api_key=os.getenv("VOYAGE_API_KEY"),
    )

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_PATH,
    )
    print(f"✓ Vector store built and persisted to {CHROMA_PATH}")
    return vector_store


def test_retrieval(vector_store: Chroma) -> None:
    """Quick sanity check — query the vector store with example questions."""
    print("\n── Retrieval sanity check ───────────────────────────────────────")
    test_queries = [
        "Quais são as taxas da Maquininha Smart?",
        "Como usar o celular como maquininha?",
        "O que é o Pix Parcelado?",
    ]
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = vector_store.similarity_search(query, k=2)
        for i, doc in enumerate(results):
            print(f"  Result {i+1} ({doc.metadata.get('source', 'unknown')}):")
            print(f"  {doc.page_content[:150]}...")


if __name__ == "__main__":
    print("═" * 60)
    print("InfinitePay RAG Ingestion Pipeline")
    print("═" * 60)

    # Step 1: Scrape
    documents = scrape_urls(URLS)
    if not documents:
        print("✗ No documents scraped. Check your internet connection.")
        exit(1)

    # Step 2: Chunk
    chunks = chunk_documents(documents)

    # Step 3: Embed + Store
    vector_store = build_vector_store(chunks)

    # Step 4: Verify
    test_retrieval(vector_store)

    print("\n═" * 60)
    print("✓ Ingestion complete. Vector store ready at:", CHROMA_PATH)
    print("═" * 60)