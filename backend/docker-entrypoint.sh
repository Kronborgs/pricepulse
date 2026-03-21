#!/bin/bash
set -e

PGDATA=/var/lib/postgresql/data
PGUSER="${POSTGRES_USER:-pricepulse}"
PGPASSWORD="${POSTGRES_PASSWORD:-changeme}"
PGDB="${POSTGRES_DB:-pricepulse}"

# ─── Initialise PostgreSQL data directory if empty ────────────────────────────
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "[entrypoint] Initialising PostgreSQL..."
    su -c "/usr/lib/postgresql/16/bin/initdb -D $PGDATA --username=postgres --encoding=UTF8" postgres
fi

# ─── Start PostgreSQL + Redis via supervisord in background ───────────────────
echo "[entrypoint] Starting PostgreSQL and Redis..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/pricepulse.conf &
SUPERVISOR_PID=$!

# ─── Wait for PostgreSQL to be ready ─────────────────────────────────────────
echo "[entrypoint] Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    if su -c "pg_isready -q" postgres 2>/dev/null; then
        echo "[entrypoint] PostgreSQL is ready."
        break
    fi
    sleep 1
done

# ─── Create database user and database if they don't exist ────────────────────
su -c "psql -U postgres -tc \"SELECT 1 FROM pg_roles WHERE rolname='$PGUSER'\" | grep -q 1 \
    || psql -U postgres -c \"CREATE USER $PGUSER WITH PASSWORD '$PGPASSWORD'\"" postgres

su -c "psql -U postgres -tc \"SELECT 1 FROM pg_database WHERE datname='$PGDB'\" | grep -q 1 \
    || psql -U postgres -c \"CREATE DATABASE $PGDB OWNER $PGUSER\"" postgres

# ─── Wait for Redis ───────────────────────────────────────────────────────────
echo "[entrypoint] Waiting for Redis..."
for i in $(seq 1 15); do
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        echo "[entrypoint] Redis is ready."
        break
    fi
    sleep 1
done

# ─── Run Alembic migrations ───────────────────────────────────────────────────
echo "[entrypoint] Running database migrations..."
cd /app
DATABASE_URL="postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@127.0.0.1:5432/${PGDB}" \
    alembic upgrade head

# ─── Start FastAPI via supervisord ────────────────────────────────────────────
echo "[entrypoint] Starting API..."
supervisorctl start api

# ─── Keep container alive ─────────────────────────────────────────────────────
wait $SUPERVISOR_PID
