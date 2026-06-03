#!/bin/bash
set -e

echo "Starting InfinitePay Agent Swarm..."

# Seed database if it doesn't exist (fast, ~1 second)
if [ ! -f "/app/data/infinitepay_users.db" ]; then
    echo "Seeding user database..."
    python -m data.seed_users
    echo "Database seeded."
fi

# Run ingestion in background if ChromaDB doesn't exist
if [ ! -d "/app/data/chroma_db" ]; then
    echo "ChromaDB not found. Starting ingestion in background..."
    python -m ingestion.scrape &
    echo "Ingestion running in background. API starting now."
else
    echo "ChromaDB found. Skipping ingestion."
fi

# Start API immediately (don't wait for ingestion)
echo "Starting API server..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000