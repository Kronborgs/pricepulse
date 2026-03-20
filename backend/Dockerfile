# ─── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Installér system-afhængigheder (til psycopg2 / lxml)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Installér Python-afhængigheder
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user
RUN groupadd -g 1001 appgroup \
    && useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# System runtime-deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiér installerede packages fra builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Kopiér app-kode
COPY --chown=appuser:appgroup . .

# Data-mappe til evt. lokal fil-storage
RUN mkdir -p /app/data && chown appuser:appgroup /app/data

USER appuser

EXPOSE 8000

# Kør migrationer, derefter start API
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
