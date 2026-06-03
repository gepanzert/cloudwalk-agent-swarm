#!/bin/bash
set -e

echo "Starting InfinitePay Agent Swarm..."

# Run ingestion if ChromaDB doesn't exist
if [ ! -d "/app/data/chroma_db" ]; then
    echo "ChromaDB not found. Running ingestion pipeline..."
    python -m ingestion.scrape
    echo "Ingestion complete."
else
    echo "ChromaDB found. Skipping ingestion."
fi

# Seed database if it doesn't exist
if [ ! -f "/app/data/infinitepay_users.db" ]; then
    echo "User database not found. Seeding..."
    python -m data.seed_users
    echo "Database seeded."
else
    echo "User database found. Skipping seed."
fi

# Start the API
echo "Starting API server..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
