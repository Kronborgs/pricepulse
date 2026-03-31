<div align="center">
  <img src="assets/icon.png" alt="PricePulse" width="80" />
  <h1>PricePulse</h1>
  <p><strong>Self-hosted prisovervågning til danske webshops</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
    <img src="https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
    <img src="https://img.shields.io/badge/Unraid-compatible-F15A2C" alt="Unraid" />
  </p>
</div>

---

PricePulse holder øje med priser på tværs af danske webshops og sender dig besked, når prisen falder eller en vare kommer tilbage på lager. Alt kører lokalt i din egen infrastruktur  ingen cloud, ingen abonnement.

## Skærmbilleder

<!-- SCREENSHOT-GUIDE
     Alle billeder tages i browseren med PricePulse kørende (mørkt tema).
     Gem som PNG, helst 1400-1600px bred, i mappen assets/screenshots/.
-->

### Dashboard
![Dashboard](assets/screenshots/dashboard.png)
> **Tag screenshot af:** Hele dashboard-siden — stats-rækken øverst (antal watches, aktive, fejl, prisfald i dag), seneste prisændringer i midten, og evt. fejl-banneret i bunden.

### Watches — oversigt
![Watches](assets/screenshots/watches.png)
> **Tag screenshot af:** Watch-listen med statusfiltre øverst (Alle / Aktiv / Afventer / AI / Pause / Fejl / Blokeret), søgefelt, og et par rækker watches med statusbadges og priser.

### Watch — detalje & prisgraf
![Watch detalje](assets/screenshots/watch-detail.png)
> **Tag screenshot af:** En enkelt watch åbnet — prisgrafen i toppen, kilde-listen nedenunder med butikslogoer og priser side om side, og "Rapportér fejl"-knappen.

### Produkter
![Produkter](assets/screenshots/products.png)
> **Tag screenshot af:** Produktoversigten med søgefelt, et par produktkort med billede og bedste pris, og gerne duplikat-advarslen øverst hvis der er nogen.

### Notifikationspræferencer
![Notifikationer](assets/screenshots/notifications.png)
> **Tag screenshot af:** Siden `/me/preferences` — Hændelsesnotifikationer (Prisfald, Tilbage på lager, Enhver ændring, Fejl), Digest-e-mail med frekvens- og dagvælger, og “Send test-e-mail”-knappen.

### Indstillinger — Backup
![Backup](assets/screenshots/backup.png)
> **Tag screenshot af:** Settings-siden åben på Backup-sektionen — vis automatisk backup-konfiguration, SMTP-info-noten, og backup-listen med en eller flere filer.

### Første opsætning
![Setup](assets/screenshots/setup.png)
> **Tag screenshot af:** Setup-guiden (åbnes automatisk ved ny installation) — vis de to faner "Ny konto" og "Gendan backup".

### Admin — Brugere
![Brugere](assets/screenshots/admin-users.png)
> **Tag screenshot af:** Admin → Brugere — brugertabellen med rolle-badges (admin/superuser/user), status, session-timeout og Deaktiver/Slet-knapper. Gerne med mindst to brugere synlige.

### Admin — SMTP
![SMTP](assets/screenshots/smtp.png)
> **Tag screenshot af:** Admin → SMTP-siden med konfigurationsformularen udfyldt. Vis at status står "Konfigureret".

### Admin — Scraper-rapporter
![Rapporter](assets/screenshots/admin-reports.png)
> **Tag screenshot af:** Admin → Rapporter — vis fanerne (Alle/Nye/Læst/Løst), et par rapportkort med statusbadge, bruger-navn, watch-link og action-knapper (Markér læst / Løst / Slet).

### Global SMTP-advarsel
![SMTP banner](assets/screenshots/smtp-banner.png)
> **Tag screenshot af:** En hvilken som helst side (f.eks. dashboard) hvor SMTP-banneret vises øverst — det amber-farvede banner med "SMTP ikke konfigureret" og knappen "Opsæt SMTP".

---

## Funktioner

| Område | Hvad det gør |
|--------|-------------|
| **Prisovervågning** | Følger en eller flere butikskilder pr. produkt og registrerer hvert prisfald og lagerændring |
| **Multi-kilde sammenligning** | Viser alle butikspriser på samme produkt side om side med prisgraf pr. kilde |
| **Produktkatalog** | Samler watch-kilder under ét produkt og foreslår automatisk mulige dubletter |
| **E-mail notifikationer** | Prisfald, lager, enhver ændring eller fejl — konfigurerbart pr. bruger med valg af frekvens (straks/daglig/ugentlig/månedlig) |
| **Digest-e-mail** | Periodisk oversigt over alle ændringer — daglig, ugentlig eller månedlig med valgfri dag |
| **AI-assistent (Ollama)** | Analyserer sider der fejler og foreslår CSS-selectors, Playwright-behov og bot-beskyttelse |
| **Automatisk backup** | Tidsplanlagt backup af hele databasen til disk — download, gendan eller importer til ny server |
| **Brugeradministration** | Fler-bruger support med roller (admin/superuser/bruger), invitation via e-mail, session-timeout |
| **Scraper-rapporter** | Brugere kan rapportere fejl på en kilde direkte fra UI — admin/superuser håndterer og løser rapporter |
| **Scraper-engine** | HTTP (httpx) og JavaScript-rendering (Playwright), pluggable parsers: CSS, JSON-LD, inline JSON |
| **Fejlklassificering** | Kategoriserer fejl: parser-mismatch, JS-render krævet, bot-beskyttelse, timeout, HTTP-fejl |

---

## Roller og rettigheder

PricePulse har tre brugerroller. Den første konto der oprettes ved opsætning er altid **admin**.

| Funktion | Bruger | Superuser | Admin |
|---|:---:|:---:|:---:|
| Dashboard, watches, produkter (egne) | ✅ | ✅ | ✅ |
| Se alle brugeres watches og produkter | ❌ | ✅ | ✅ |
| Opret og rediger watches/produkter | ✅ | ✅ | ✅ |
| Indstil notifikationspræferencer | ✅ | ✅ | ✅ |
| **Admin: Brugeroversigt** | ❌ | ✅ | ✅ |
| Opret nye brugere (invitation) | ❌ | ✅ | ✅ |
| Slet brugere med rollen 'bruger' | ❌ | ✅ | ✅ |
| Slet brugere med rollen 'superuser' eller 'admin' | ❌ | ❌ | ✅ |
| **Admin: Scraper-rapporter** | ❌ | ✅ | ✅ |
| **Admin: AI Job Log** | ❌ | ✅ | ✅ |
| **Admin: SMTP-konfiguration** | ❌ | ❌ | ✅ |
| **Admin: Datahåndtering** (slet data, overtag ressourcer) | ❌ | ❌ | ✅ |
| **Indstillinger: Butikker** (aktivér/deaktivér, rediger) | ❌ (skrivebeskyttet) | ❌ (skrivebeskyttet) | ✅ |
| **Indstillinger: Backup** (start, download, gendan, konfigurér) | ❌ (skrivebeskyttet) | ❌ (skrivebeskyttet) | ✅ |
| **Indstillinger: Ollama** (AI-host, modeller) | ❌ (skrivebeskyttet) | ✅ | ✅ |

> **Første opsætning:** Opsætnings-wizarden opretter automatisk systemets første admin-konto. Efterfølgende brugere inviteres via Admin → Brugere og modtager et link til at oprette deres kodeord.

---

## Quick Start

```bash
git clone https://github.com/Kronborgs/pricepulse.git
cd pricepulse
cp .env.example .env
# Redigér .env  se sektionen Miljø-variabler nedenfor
docker compose up -d
```

- **Web UI:** `http://localhost:3000`
- **API docs:** `http://localhost:8000/docs`

Forste gang du abner UI'en guides du igennem opsætnings-wizarden, hvor du opretter din admin-konto (eller gendanner fra en eksisterende backup).

---

## Opsetning pa Unraid

PricePulse kører som en Docker Compose-stack pa Unraid via **Compose Manager** (Community Applications plugin).

### Forudsætninger

1. **Community Applications** installeret (søg i Apps -> "Community Applications")
2. **Compose Manager** installeret via Community Applications
3. Git installeret på Unraid (`Nerd Tools` plugin -> installer `git`)

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
| `FERNET_KEY` | Se nedenfor | **Vigtigt:** bevar denne på tværs af deployments, ellers mistes krypterede SMTP-adgangskoder |
| `POSTGRES_PASSWORD` | `MitSterkePassword123` | Vælg selv |
| `DATABASE_URL` | Se nedenfor | Skal matche POSTGRES_PASSWORD |
| `NEXT_PUBLIC_API_URL` | `http://192.168.1.XX:8000` | Din Unraid-servers LAN-IP |
| `CORS_ORIGINS` | `http://192.168.1.XX:3000` | Samme IP, port 3000 |
| `TZ` | `Europe/Copenhagen` | Tidszone |

**Generér `FERNET_KEY` én gang og gem den:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
> Sæt den genererede nøgle i `.env` som `FERNET_KEY=...` og bevar den ved fremtidige opdateringer.
> Hvis nøglen ændres eller fjernes, kan gemte SMTP-adgangskoder **ikke** longer dekrypteres.

**DATABASE_URL skal matche dit password:**
```
DATABASE_URL=postgresql+asyncpg://pricepulse:MitSterkePassword123@db:5432/pricepulse
```

#### 3. Tilføj stacken i Compose Manager

1. Gå til **Unraid webUI -> Docker -> Compose Manager**
2. Klik **Add New Stack**
3. Navn: `pricepulse`
4. Compose file path: `/mnt/user/appdata/pricepulse/docker-compose.yml`
5. Env file path: `/mnt/user/appdata/pricepulse/.env`
6. Klik **Save**
7. Klik **Start** pa stacken

#### 4. Abn appen og gennemfor opsetningen

Gå til `http://DIN-UNRAID-IP:3000`  opsætnings-wizarden starter automatisk første gang. Opret din admin-konto eller gendan fra en eksisterende backup.

> Forste gang du installerer oprettes butikker (Komplett, Proshop, mfl.) automatisk af migrationen. Du behøver ikke køre `seed` manuelt.

#### 5. Porte

| Service | Port | Kan ændres via |
|---|---|---|
| Frontend (UI) | 3000 | `FRONTEND_PORT=XXXX` i `.env` |
| Backend (API) | 8000 | `BACKEND_PORT=XXXX` i `.env` |

---

### Unraid Community Applications  ikon

**Icon URL:**
```
https://raw.githubusercontent.com/Kronborgs/pricepulse/main/assets/icon.png
```

---

### Unraid Docker-templates (enkelt-container opsætning)

Foretrækker du at køre PricePulse som **individuelle Docker-containere** i stedet for Compose Manager, kan du bruge de færdige Unraid-templates fra mappen `unraid/`.

#### Metode 1 — Gem lokalt på Unraid (anbefalet)

SSH ind på din Unraid-server og kør:

```bash
mkdir -p /boot/config/plugins/dockerMan/templates-user
wget -O /boot/config/plugins/dockerMan/templates-user/pricepulse-backend.xml \
  https://raw.githubusercontent.com/Kronborgs/pricepulse/main/unraid/pricepulse-backend.xml
wget -O /boot/config/plugins/dockerMan/templates-user/pricepulse.xml \
  https://raw.githubusercontent.com/Kronborgs/pricepulse/main/unraid/pricepulse.xml
```

Herefter vises de under **Docker → Add Container** i Unraid-menuen.

#### Metode 2 — Manuelt

1. Download `unraid/pricepulse-backend.xml` og `unraid/pricepulse.xml` fra dette repo
2. Kopier begge filer til `/boot/config/plugins/dockerMan/templates-user/` på din Unraid-server (via SMB: `\\UNRAID\flash\config\plugins\dockerMan\templates-user\`)
3. Åbn **Docker → Add Container** — templatene dukker nu op under "User Templates"

#### Rækkefølge og vigtige variabler

Start **pricepulse-backend** først og vent til den er oppe, før du starter **pricepulse** (frontend).

| Container | Variabel | LAN (plain HTTP) | Cloudflare tunnel / HTTPS |
|---|---|---|---|
| `pricepulse-backend` | `CORS_ORIGINS` | `http://192.168.1.50:3000` | `https://prisen.ditdomæne.dk` |
| `pricepulse-backend` | `FRONTEND_URL` | `http://192.168.1.50:3000` | `https://prisen.ditdomæne.dk` |
| `pricepulse-backend` | `COOKIE_SECURE` | `false` | `true` |
| `pricepulse` | `NEXT_PUBLIC_API_URL` | `http://pricepulse-backend:8000` | `http://pricepulse-backend:8000` |

> `FRONTEND_URL` styrer hvilken URL der indsættes i e-mails (notifikationer, glemt kodeord, afmeld-links). Sæt den til den adresse **brugeren** åbner PricePulse med.

---


```bash
cd /mnt/user/appdata/pricepulse
git pull
docker compose pull
docker compose up -d
```

Eller i **Compose Manager**: klik **Pull** og derefter **Restart**.

---

## Releases og versionering

Versioner følger formatet **`v[YYYYMMDD]v[N]`**  dato + build-nummer samme dag:

| Tag | Hvornaar |
|---|---|
| `v20260320v1` | Første release den 20. marts 2026 |
| `v20260320v2` | Anden ændring samme dag |
| `v20260321v1` | Første release næste dag |

```bash
# Tag og publicér en ny version
git tag v20260329v1
git push origin v20260329v1
```

GitHub Actions bygger og pusher automatisk til `ghcr.io/kronborgs/pricepulse-backend:latest` og `ghcr.io/kronborgs/pricepulse-frontend:latest`.

---

## E-mail notifikationer (SMTP)

SMTP konfigureres under **Admin -> SMTP** i web-UI'en. Hvis SMTP ikke er sat op, vises en advarsel overst pa alle sider (kun synlig for admins).

> **Bemærk:** SMTP-kodeordet gemmes **ikke** i backup af sikkerhedsmæssige årsager. Øvrige SMTP-indstillinger gendannes ved restore, men som deaktiverede  genindtast kodeordet under Admin -> SMTP for at aktivere notifikationer igen.

---

## Backup & restore

Backups gemmes automatisk (eller manuelt) under **Indstillinger -> Backup**.

- Filer gemmes i `/app/data/backup` (Unraid: `/mnt/user/appdata/pricepulse/backup`)
- Download backup-filen lokalt som `.json.gz`
- Gendan direkte fra listen, eller upload en fil fra en anden installation
- Ved **Ny installation**: Opsætnings-wizarden tilbyder "Gendan backup" som alternativ til at oprette en ny konto

---

## Stack

| Lag | Teknologi |
|-----|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async) |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Scraping | httpx + Playwright |
| AI (valgfrit) | Ollama (lokal LLM til parser-analyse) |
| Charts | Recharts |
| Scheduling | APScheduler |

---

## Fejlfinding

```bash
# Se alle container-logs
docker compose logs -f

# Kun backend
docker logs pricepulse-backend -f

# Kun frontend
docker logs pricepulse-frontend -f

# Database shell
docker exec -it pricepulse-db psql -U pricepulse
```

---

## Miljø-variabler

Se [.env.example](.env.example) for komplet liste.

---

## Licens

MIT