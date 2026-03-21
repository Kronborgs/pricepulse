# ─── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Runtime stage (all-in-one: FastAPI + PostgreSQL 16 + Redis 7) ─────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# PostgreSQL 16 + Redis 7 + supervisord + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    redis-server \
    supervisor \
    gnupg \
    lsb-release \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] \
       https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends \
       postgresql-16 \
    && rm -rf /var/lib/apt/lists/*

# Kopiér Python packages fra builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Kopiér app-kode
COPY . .

# Data-mapper
RUN mkdir -p /app/data /var/lib/postgresql/data /var/run/postgresql \
    && chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql

# supervisord config
COPY supervisord.conf /etc/supervisor/conf.d/pricepulse.conf

# Startup scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY start-api.sh /app/start-api.sh
RUN chmod +x /docker-entrypoint.sh /app/start-api.sh

EXPOSE 8000

CMD ["/docker-entrypoint.sh"]
