#!/bin/bash
PGUSER="${POSTGRES_USER:-pricepulse}"
PGPASSWORD="${POSTGRES_PASSWORD:-changeme}"
PGDB="${POSTGRES_DB:-pricepulse}"

export DATABASE_URL="postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@127.0.0.1:5432/${PGDB}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
