# PricePulse

Self-hosted prisovervågningssystem til danske webshops. Kører stabilt som Docker-container på Unraid.

## Features

- **Multi-shop overvågning** — compumail, computersalg, elsalg, happii, komplett, proshop og mere
- **Prishistorik** — interaktive grafer over prisudvikling over tid
- **Multi-store sammenligning** — se samme vare fra flere butikker i ét overblik
- **Modulær scraper-arkitektur** — HTTP og Playwright providers, pluggable parsers
- **Robust fejlhåndtering** — rate limiting, retry, tydelig status ved blokering
- **Moderne dashboard** — clean UI med TailwindCSS og shadcn/ui

## Quick Start

```bash
# Klon repo og kopiér env-fil
git clone https://github.com/Kronborgs/pricepulse.git
cd pricepulse
cp .env.example .env

# Start alle services
docker compose up -d

# Se logs
docker compose logs -f backend
```

Frontend: http://localhost:3000  
API docs: http://localhost:8000/docs

## Opsætning på Unraid

PricePulse kører som en Docker Compose-stack på Unraid via **Compose Manager** (Community Applications plugin).

### Forudsætninger

1. **Community Applications** installeret (søg i Apps → "Community Applications")
2. **Compose Manager** installeret via Community Applications
3. Git installeret på Unraid (`Nerd Tools` plugin → installer `git`)

---

### Trin-for-trin

#### 1. Klon projektet til Unraid

SSH ind på din Unraid-server og kør:

```bash
cd /mnt/user/appdata
git clone https://github.com/Kronborgs/pricepulse.git
cd pricepulse
```

#### 2. Opret din `.env`-fil

```bash
cp .env.example .env
nano .env
```

Minimum du **skal** ændre:

| Variabel | Eksempel | Beskrivelse |
|---|---|---|
| `SECRET_KEY` | `$(openssl rand -hex 32)` | Generes med kommandoen i parentes |
| `POSTGRES_PASSWORD` | `MitSterkePassword123` | Vælg selv |
| `DATABASE_URL` | Se nedenfor | Skal matche POSTGRES_PASSWORD |
| `NEXT_PUBLIC_API_URL` | `http://192.168.1.XX:8000` | Din Unraid-servers LAN-IP |
| `CORS_ORIGINS` | `http://192.168.1.XX:3000` | Samme IP, port 3000 |
| `TZ` | `Europe/Copenhagen` | Tidszone |

**DATABASE_URL skal matche dit password:**
```
DATABASE_URL=postgresql+asyncpg://pricepulse:MitSterkePassword123@db:5432/pricepulse
```

#### 3. Tilføj stacken i Compose Manager

1. Gå til **Unraid webUI → Docker → Compose Manager**
2. Klik **Add New Stack**
3. Navn: `pricepulse`
4. Compose file path: `/mnt/user/appdata/pricepulse/docker-compose.yml`
5. Env file path: `/mnt/user/appdata/pricepulse/.env`
6. Klik **Save**
7. Klik **Start** på stacken

#### 4. Seed databasen (første gang)

Vent ca. 30 sekunder til alle containers er oppe, kør derefter:

```bash
docker exec pricepulse-backend python -m app.scripts.seed
```

Dette tilføjer de 6 danske butikker (compumail, computersalg, elsalg, happii, komplett, proshop).

#### 5. Åbn appen

- **Frontend:** `http://DIN-UNRAID-IP:3000`
- **API docs:** `http://DIN-UNRAID-IP:8000/docs`

---

### Porte

| Service | Port | Kan ændres via |
|---|---|---|
| Frontend (UI) | 3000 | `FRONTEND_PORT=XXXX` i `.env` |
| Backend (API) | 8000 | `BACKEND_PORT=XXXX` i `.env` |

---

### Unraid Community Applications — Icon

Hvis du ønsker PricePulse som et ikon i Unraid's Docker-oversigt, kan du bruge dette ikon:

**Icon URL:**
```
https://raw.githubusercontent.com/Kronborgs/pricepulse/main/assets/icon.png
```

Filen ligger allerede i `assets/icon.png` i repo'et.

---

### Opdatering

SSH ind og kør:

```bash
cd /mnt/user/appdata/pricepulse
git pull
docker compose pull
docker compose up -d
```

Eller i **Compose Manager**: klik **Pull** og derefter **Restart**.

---

## Releases og versionering

Versioner følger formatet **`v[YYYYMMDD]v[N]`** — dato + build-nummer samme dag:

| Tag | Hvornår |
|---|---|
| `v20260320v1` | Første release den 20. marts 2026 |
| `v20260320v2` | Anden ændring samme dag |
| `v20260321v1` | Første release næste dag |

### Udgiv en ny version

```bash
# Første release i dag
git tag v20260320v1
git push origin v20260320v1

# Endnu en ændring samme dag
git tag v20260320v2
git push origin v20260320v2
```

GitHub Actions bygger og pusher automatisk:
- `ghcr.io/kronborgs/pricepulse-backend:v20260320v1`
- `ghcr.io/kronborgs/pricepulse-backend:latest`
- `ghcr.io/kronborgs/pricepulse-frontend:v20260320v1`
- `ghcr.io/kronborgs/pricepulse-frontend:latest`

Unraid henter `:latest` automatisk når du klikker **Pull** i Compose Manager.

---

### Fejlfinding

```bash
# Se alle container-logs
docker compose -f /mnt/user/appdata/pricepulse/docker-compose.yml logs -f

# Kun backend
docker logs pricepulse-backend -f

# Kun frontend
docker logs pricepulse-frontend -f

# Database shell
docker exec -it pricepulse-db psql -U pricepulse
```

## Stack

| Lag | Teknologi |
|-----|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async) |
| Frontend | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Scraping | httpx + Playwright |
| Charts | Recharts |

## Miljø-variabler

Se [.env.example](.env.example) for komplet liste.

## Docker Compose Services

```
backend   — FastAPI + APScheduler (port 8000)
frontend  — Next.js UI (port 3000)
db        — PostgreSQL 16
redis     — Redis 7
```

## Licens

MIT
