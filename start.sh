#!/bin/bash

echo "Starting RAG API..."
echo "PORT: ${PORT:-8000}"

# Set default port if not provided
export PORT=${PORT:-8000}

# Start the application
python -m uvicorn src.api.app:app --host 0.0.0.0 --port $PORT --workers 1
