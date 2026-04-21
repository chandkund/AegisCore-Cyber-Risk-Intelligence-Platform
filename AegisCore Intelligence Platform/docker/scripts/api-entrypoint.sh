#!/bin/bash
set -e

echo "Checking database connectivity..."

# Wait for database to be ready (with timeout)
MAX_RETRIES=30
RETRY_COUNT=0

while ! python -c "from app.db.session import engine; from sqlalchemy import text; conn = engine.connect(); conn.execute(text('SELECT 1')); conn.close()" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: Database not available after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "Database is ready"

# Check if alembic is initialized
if ! alembic current >/dev/null 2>&1; then
    echo "Initializing alembic version table..."
    alembic stamp head 2>/dev/null || true
fi

# Run migrations - deterministic, always use Alembic
echo "Running migrations (alembic upgrade head)..."
alembic upgrade head

# Verify migrations applied
CURRENT=$(alembic current 2>/dev/null || echo "unknown")
echo "Current migration: $CURRENT"

echo "Starting application..."
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
