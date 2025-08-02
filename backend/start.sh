#!/bin/bash

# Start script for ViralOS backend

echo "Starting ViralOS Backend..."

# Check if database is ready
echo "Waiting for database to be ready..."
sleep 5

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Initialize database if needed
echo "Initializing database..."
python -c "from app.db.init_db import init_db; init_db()"

# Start the application
echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload