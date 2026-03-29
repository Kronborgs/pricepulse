#!/bin/bash
set -e

PGDATA=/app/data/postgres
PGUSER="${POSTGRES_USER:-pricepulse}"
PGPASSWORD="${POSTGRES_PASSWORD:-changeme}"
PGDB="${POSTGRES_DB:-pricepulse}"

# ─── Opret data-mapper hvis de ikke findes ────────────────────────────────────
mkdir -p /app/data/postgres /app/data/redis
chown postgres:postgres /app/data/postgres
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "[entrypoint] Initialising PostgreSQL..."
    su -c "/usr/lib/postgresql/16/bin/initdb -D $PGDATA --username=postgres --encoding=UTF8" postgres
fi

# ─── Start PostgreSQL + Redis via supervisord in background ─────────────────
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

# ─── Extra: wait until the target database actually accepts connections ────────
echo "[entrypoint] Verifying database connection..."
for i in $(seq 1 20); do
    if su -c "psql -U postgres -d postgres -c 'SELECT 1' -q > /dev/null 2>&1" postgres; then
        echo "[entrypoint] Database connection verified."
        break
    fi
    echo "[entrypoint] Database not accepting connections yet (attempt $i)..."
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

# ─── Run Alembic migrations (med retry ved connection-fejl) ──────────────────
echo "[entrypoint] Running database migrations..."
cd /app
for i in $(seq 1 5); do
    DATABASE_URL="postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@127.0.0.1:5432/${PGDB}" \
        alembic upgrade head && break
    echo "[entrypoint] Migration attempt $i failed, retrying in 3s..."
    sleep 3
done

# ─── Start FastAPI via supervisord ────────────────────────────────────────────
echo "[entrypoint] Starting API..."
supervisorctl -c /etc/supervisor/conf.d/pricepulse.conf start api

# ─── Keep container alive ─────────────────────────────────────────────────────
wait $SUPERVISOR_PID
