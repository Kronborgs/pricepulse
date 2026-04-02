<div align="center">
  <img src="assets/icon.png" alt="PricePulse" width="80" />
  <h1>PricePulse</h1>
  <p><strong>Self-hosted price monitoring for web shops</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
    <img src="https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
    <img src="https://img.shields.io/badge/Unraid-compatible-F15A2C" alt="Unraid" />
  </p>
</div>

---

PricePulse monitors prices across web shops and notifies you when a price drops or an item comes back in stock. Everything runs locally in your own infrastructure — no cloud, no subscription.

## Screenshots

<!-- SCREENSHOT-GUIDE
     All screenshots are taken in the browser with PricePulse running (dark theme).
     Save as PNG, preferably 1400-1600px wide, in the assets/screenshots/ folder.
-->

### Dashboard
![Dashboard](assets/screenshots/dashboard.png)
> **Screenshot should show:** The full dashboard page — the stats row at the top (number of watches, active, errors, price drops today), recent price changes in the middle, and optionally the error banner at the bottom.

### Watches — overview
![Watches](assets/screenshots/watches.png)
> **Screenshot should show:** The watch list with status filters at the top (All / Active / Pending / AI / Paused / Error / Blocked), search field, and a few rows of watches with status badges and prices. The data scraper is opened via the Products page or directly at `/watches`.

### Watch — detail & price chart
![Watch detail](assets/screenshots/watch-detail.png)
> **Screenshot should show:** A single watch opened — the price chart at the top (AreaChart with gradient and IQR y-axis), the source list below with shop logos and prices side by side, and the "Report issue" button.

### Products — overview with tags
![Products](assets/screenshots/products.png)
> **Screenshot should show:** The product overview with search field, tag filter pills below the search field, a few product cards with image, best price and tag badges, and ideally the duplicate warning at the top. Note the **Data scraper** and **Add watch** buttons in the top-right corner.

### Product — detail with tag editor
![Product detail](assets/screenshots/product-detail.png)
> **Screenshot should show:** A single product page opened — product name, the tag editor with a few tags and the input field ("Add tags…"), the multi-source price chart below, and the "Merge" button.

### Product — multi-source price chart
![Multi-source price chart](assets/screenshots/product-chart.png)
> **Screenshot should show:** Zoomed in on the price chart on a product page — show AreaChart with gradient-filled curves for at least two shops, the "Cheapest now" banner and the Custom/MUI X toggle button in the top-right.

### Notification preferences
![Notifications](assets/screenshots/notifications.png)
> **Screenshot should show:** The `/me/preferences` page — Event notifications (Price drop, Back in stock, Any change, Error), Digest email with frequency and day selector, and the "Send test email" button.

### Settings — Backup
![Backup](assets/screenshots/backup.png)
> **Screenshot should show:** The Settings page open on the Backup section — show the automatic backup configuration, the SMTP info note, and the backup list with one or more files.

### Initial setup
![Setup](assets/screenshots/setup.png)
> **Screenshot should show:** The setup wizard (opens automatically on a fresh installation) — show the two tabs "New account" and "Restore backup".

### Admin — Users
![Users](assets/screenshots/admin-users.png)
> **Screenshot should show:** Admin → Users — the user table with role badges (admin/superuser/user), status, session timeout and Deactivate/Delete buttons. Ideally with at least two users visible.

### Admin — SMTP
![SMTP](assets/screenshots/smtp.png)
> **Screenshot should show:** Admin → SMTP page with the configuration form filled in. Show that the status reads "Configured".

### Admin — Scraper reports
![Reports](assets/screenshots/admin-reports.png)
> **Screenshot should show:** Admin → Reports — show the tabs (All/New/Read/Resolved), a few report cards with status badge, username, watch link and action buttons (Mark read / Resolved / Delete).

### Global SMTP warning
![SMTP banner](assets/screenshots/smtp-banner.png)
> **Screenshot should show:** Any page (e.g. dashboard) where the SMTP banner is shown at the top — the amber-coloured banner with "SMTP not configured" and the "Set up SMTP" button.

---

## Features

| Area | What it does |
|--------|-------------|
| **Price monitoring** | Tracks one or more shop sources per product and records every price drop and stock change |
| **Currency conversion** | Prices are automatically stored in DKK via Danmarks Nationalbank’s daily exchange rates. A currency hint (EUR, USD, SEK, etc.) can be set per watch/source. Raw price and rate are shown on the detail page — e.g. `115.83 kr. / €15.50 · 1 EUR = 7.47 kr` |
| **Multi-source comparison** | Shows all shop prices for the same product side by side with an interactive AreaChart per source (gradient fill, IQR y-axis, "Cheapest now" banner) |
| **Chart selection** | Choose per product between **Custom** (Recharts AreaChart) and **MUI X** (official MUI component) via toggle in the UI |
| **Product catalogue** | Groups watch sources under a single product and automatically suggests possible duplicates |
| **Product tags** | Users add their own tags (e.g. `lego`, `aquarium`, `cpu`) directly on products — search and filter the product list by tags |
| **Product merging** | All users can merge their own products (not just admins) — consolidates all shop sources under one product |
| **Email notifications** | Price drop, back in stock, any change or error — configurable per user with choice of frequency (instant/daily/weekly/monthly) |
| **Digest email** | Periodic summary of all changes — daily, weekly or monthly with optional day selection |
| **AI assistant (Ollama)** | Analyses failing pages and suggests CSS selectors, Playwright needs and bot-protection workarounds |
| **Automatic backup** | Scheduled backup of the entire database to disk — download, restore or import to a new server |
| **User management** | Multi-user support with roles (admin/superuser/user), invitation via email, session timeout |
| **Scraper reports** | Users can report issues on a source directly from the UI — admin/superuser handles and resolves reports |
| **Scraper engine** | HTTP (httpx) and JavaScript rendering (Playwright), pluggable parsers: CSS, JSON-LD, inline JSON |
| **Error classification** | Categorises errors: parser mismatch, JS render required, bot protection, timeout, HTTP error |

---

## Roles and permissions

PricePulse has three user roles. The first account created during setup is always **admin**.

| Feature | User | Superuser | Admin |
|---|:---:|:---:|:---:|
| Dashboard, watches, products (own) | ✅ | ✅ | ✅ |
| View all users’ watches and products | ❌ | ✅ | ✅ |
| Create and edit watches/products | ✅ | ✅ | ✅ |
| Add/edit tags on own products | ✅ | ✅ | ✅ |
| Merge own products | ✅ | ✅ | ✅ |
| Set notification preferences | ✅ | ✅ | ✅ |
| **Admin: User overview** | ❌ | ✅ | ✅ |
| Create new users (invitation) | ❌ | ✅ | ✅ |
| Delete users with role 'user' | ❌ | ✅ | ✅ |
| Delete users with role 'superuser' or 'admin' | ❌ | ❌ | ✅ |
| **Admin: Scraper reports** | ❌ | ✅ | ✅ |
| **Admin: AI Job Log** | ❌ | ✅ | ✅ |
| **Admin: SMTP configuration** | ❌ | ❌ | ✅ |
| **Admin: Data management** (delete data, take over resources) | ❌ | ❌ | ✅ |
| **Settings: Shops** (enable/disable, edit) | ❌ (read-only) | ❌ (read-only) | ✅ |
| **Settings: Backup** (start, download, restore, configure) | ❌ (read-only) | ❌ (read-only) | ✅ |
| **Settings: Ollama** (AI host, models) | ❌ (read-only) | ✅ | ✅ |

> **Initial setup:** The setup wizard automatically creates the system’s first admin account. Subsequent users are invited via Admin → Users and receive a link to create their password.

---

## Quick Start

```bash
git clone https://github.com/Kronborgs/pricepulse.git
cd pricepulse
cp .env.example .env
# Edit .env  see the Environment variables section below
docker compose up -d
```

- **Web UI:** `http://localhost:3000`
- **API docs:** `http://localhost:8000/docs`

The first time you open the UI you will be guided through the setup wizard, where you create your admin account (or restore from an existing backup).

---

## Setup on Unraid

PricePulse runs as a Docker Compose stack on Unraid via **Compose Manager** (Community Applications plugin).

### Prerequisites

1. **Community Applications** installed (search in Apps → "Community Applications")
2. **Compose Manager** installed via Community Applications
3. Git installed on Unraid (`Nerd Tools` plugin → install `git`)

---

### Step-by-step

#### 1. Clone the project to Unraid

SSH into your Unraid server and run:

```bash
cd /mnt/user/appdata
git clone https://github.com/Kronborgs/pricepulse.git
cd pricepulse
```

#### 2. Create your `.env` file

```bash
cp .env.example .env
nano .env
```

The minimum you **must** change:

| Variable | Example | Description |
|---|---|---|
| `SECRET_KEY` | `$(openssl rand -hex 32)` | Generated with the command in parentheses |
| `FERNET_KEY` | See below | **Important:** preserve this across deployments, otherwise encrypted SMTP passwords are lost |
| `POSTGRES_PASSWORD` | `MyStrongPassword123` | Choose your own |
| `DATABASE_URL` | See below | Must match POSTGRES_PASSWORD |
| `NEXT_PUBLIC_API_URL` | `http://192.168.1.XX:8000` | Your Unraid server’s LAN IP |
| `CORS_ORIGINS` | `http://192.168.1.XX:3000` | Same IP, port 3000 |
| `TZ` | `Europe/Copenhagen` | Timezone |

**Generate `FERNET_KEY` once and save it:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
> Set the generated key in `.env` as `FERNET_KEY=...` and preserve it on future updates.
> If the key is changed or removed, saved SMTP passwords **cannot** be decrypted.

**DATABASE_URL must match your password:**
```
DATABASE_URL=postgresql+asyncpg://pricepulse:MyStrongPassword123@db:5432/pricepulse
```

#### 3. Add the stack in Compose Manager

1. Go to **Unraid webUI → Docker → Compose Manager**
2. Click **Add New Stack**
3. Name: `pricepulse`
4. Compose file path: `/mnt/user/appdata/pricepulse/docker-compose.yml`
5. Env file path: `/mnt/user/appdata/pricepulse/.env`
6. Click **Save**
7. Click **Start** on the stack

#### 4. Open the app and complete the setup

Go to `http://YOUR-UNRAID-IP:3000` — the setup wizard starts automatically the first time. Create your admin account or restore from an existing backup.

> The first time you install, shops (Komplett, Proshop, etc.) are automatically created by the migration. You do not need to run `seed` manually.

#### 5. Ports

| Service | Port | Can be changed via |
|---|---|---|
| Frontend (UI) | 3000 | `FRONTEND_PORT=XXXX` in `.env` |
| Backend (API) | 8000 | `BACKEND_PORT=XXXX` in `.env` |

---

### Unraid Community Applications icon

**Icon URL:**
```
https://raw.githubusercontent.com/Kronborgs/pricepulse/main/assets/icon.png
```

---

### Unraid Docker templates (single-container setup)

If you prefer to run PricePulse as **individual Docker containers** instead of Compose Manager, you can use the ready-made Unraid templates from the `unraid/` folder.

#### Method 1 — Save locally on Unraid (recommended)

SSH into your Unraid server and run:

```bash
mkdir -p /boot/config/plugins/dockerMan/templates-user
wget -O /boot/config/plugins/dockerMan/templates-user/pricepulse-backend.xml \
  https://raw.githubusercontent.com/Kronborgs/pricepulse/main/unraid/pricepulse-backend.xml
wget -O /boot/config/plugins/dockerMan/templates-user/pricepulse.xml \
  https://raw.githubusercontent.com/Kronborgs/pricepulse/main/unraid/pricepulse.xml
```

They will then appear under **Docker → Add Container** in the Unraid menu.

#### Method 2 — Manually

1. Download `unraid/pricepulse-backend.xml` and `unraid/pricepulse.xml` from this repo
2. Copy both files to `/boot/config/plugins/dockerMan/templates-user/` on your Unraid server (via SMB: `\\UNRAID\flash\config\plugins\dockerMan\templates-user\`)
3. Open **Docker → Add Container** — the templates will now appear under "User Templates"

#### Start order and important variables

Start **pricepulse-backend** first and wait until it is up before starting **pricepulse** (frontend).

| Container | Variable | LAN (plain HTTP) | Cloudflare tunnel / HTTPS |
|---|---|---|---|
| `pricepulse-backend` | `CORS_ORIGINS` | `http://192.168.1.50:3000` | `https://price.yourdomain.com` |
| `pricepulse-backend` | `FRONTEND_URL` | `http://192.168.1.50:3000` | `https://price.yourdomain.com` |
| `pricepulse-backend` | `COOKIE_SECURE` | `false` | `true` |
| `pricepulse` | `NEXT_PUBLIC_API_URL` | `http://pricepulse-backend:8000` | `http://pricepulse-backend:8000` |

> `FRONTEND_URL` controls which URL is inserted in emails (notifications, forgot password, unsubscribe links). Set it to the address **the user** opens PricePulse with.

---


```bash
cd /mnt/user/appdata/pricepulse
git pull
docker compose pull
docker compose up -d
```

Or in **Compose Manager**: click **Pull** and then **Restart**.

---

## Releases and versioning

Versions follow the format **`v[YYYYMMDD]v[N]`** — date + build number same day:

| Tag | When |
|---|---|
| `v20260320v1` | First release on 20 March 2026 |
| `v20260320v2` | Second change same day |
| `v20260321v1` | First release next day |

```bash
# Tag and publish a new version
git tag v20260329v1
git push origin v20260329v1
```

GitHub Actions automatically builds and pushes to `ghcr.io/kronborgs/pricepulse-backend:latest` and `ghcr.io/kronborgs/pricepulse-frontend:latest`.

---

## Currency conversion

Prices are always stored in **DKK** in the database. When a source is on a foreign site (e.g. Amazon .de/.com), conversion is handled automatically:

1. **Auto-detect** — the parser tries to read the currency symbol from the page (€, $, £, SEK, etc.) itself
2. **Currency hint** — you can manually specify a currency (EUR, USD, GBP, SEK, NOK, CHF, PLN) when creating a watch/source
3. **Nationalbank rates** — conversion rates are fetched daily from Danmarks Nationalbank and cached for 24 hours
4. **Raw price preserved** — the original price in the source currency is stored in `current_price_raw` / `last_price_raw` and shown on the detail page:

```
115,83 kr.
€15,50 · 1 EUR = 7,47 kr
```

> Conversion happens in `price_service.py` (v1 watches) and `source_service.py` (v2 sources). Existing watches are converted correctly on the next scrape run.

---

## Navigation

The navigation menu is organised as follows:

| Menu item | Content |
|---|---|
| **Dashboard** | Overview of active watches, recent price changes and errors |
| **Products** | Product catalogue with all monitored products |
| ↳ Buttons on the Products page | **Data scraper** (opens the watch list) and **Add watch** directly from Products |
| **Settings** | Shops, Ollama AI, Backup, SMTP (role-dependent) |
| **Admin** | AI Job Log, Users, SMTP, Data, Reports (admin/superuser only) |

> Data scraper (`/watches`) is opened via the button on the Products page. The watch list shows all monitored URLs with prices, status and the last check time.

---

## Email notifications (SMTP)

SMTP is configured under **Admin → SMTP** in the web UI. If SMTP is not set up, a warning is shown at the top of all pages (visible to admins only).

> **Note:** The SMTP password is **not** included in backups for security reasons. Other SMTP settings are restored on restore, but as disabled — re-enter the password under Admin → SMTP to re-enable notifications.

---

## Backup & restore

Backups are saved automatically (or manually) under **Settings → Backup**.

- Files are stored in `/app/data/backup` (Unraid: `/mnt/user/appdata/pricepulse/backup`)
- Download the backup file locally as `.json.gz`
- Restore directly from the list, or upload a file from another installation
- On **New installation**: The setup wizard offers "Restore backup" as an alternative to creating a new account

---

## Stack

| Layer | Technology |
|-----|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async) |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Scraping | httpx + Playwright |
| AI (optional) | Ollama (local LLM for parser analysis) |
| Charts | Recharts |
| Scheduling | APScheduler |

---

## Troubleshooting

```bash
# View all container logs
docker compose logs -f

# Backend only
docker logs pricepulse-backend -f

# Frontend only
docker logs pricepulse-frontend -f

# Database shell
docker exec -it pricepulse-db psql -U pricepulse
```

---

## Environment variables

See [.env.example](.env.example) for a complete list.

---

## Licens

MIT