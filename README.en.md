<div align="center">

# 🧬 OncoPath

**Turn scattered medical reports into a treatment journey you can actually read**

OCR lab-index extraction · Unified treatment timeline · AI-assisted interpretation · Multi-agent virtual consultation

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-early%20release-yellow.svg)](#status)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](#tech-stack)
[![Frontend](https://img.shields.io/badge/frontend-Vue%203-42b883.svg)](#tech-stack)
[![Docker](https://img.shields.io/badge/deploy-Docker%20Compose-2496ED.svg?logo=docker&logoColor=white)](#quick-start-docker)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-181717.svg?logo=github)](https://nickzhang1102.github.io/oncopath/)

[简体中文](./README.md) | **[English](./README.en.md)**

![OncoPath home indicator charts](docs/screenshots/desktop-home-indicators-chart.png)

[Project Website](https://nickzhang1102.github.io/oncopath/) · [Quick Start](#quick-start-docker) · [Screenshots](#screenshots) · [Contributing](#contributing) · [☕ Buy the author a coffee](#sponsorship)

</div>

> **Status**: This project is now public and in an early stage. Feedback is welcome. Before any production deployment, complete **every** mandatory item in the [Security](#security) section and evaluate medical-data compliance requirements in your jurisdiction.

---

## 🎯 Why OncoPath

Cancer treatment is a marathon measured in years. As a patient's family member, you have probably run into these problems:

| Reality | How OncoPath helps |
|---------|-------------------|
| 📋 Piles of lab reports — indicators and reference ranges you can't read | Snap a photo: **OCR recognition + LLM matching against a standard index library**, with professional jargon translated into plain language |
| 📁 Reports scattered across chat apps, paper folders, hospital portals | Lab / exam / pathology / medication / follow-up data **unified into one traceable treatment timeline**, filterable and exportable to PDF |
| 📉 Trends of key indicators tracked by hand in notebooks | Automatic abnormal-indicator tracking, per-indicator **trend charts + side-by-side comparison** |
| 🏥 Not sure what to ask the doctor before the visit | One-click aggregation of the full record into a consultation prompt, launching a **multi-agent virtual consultation via AgentTeams** |

OncoPath targets tech-savvy patient families and self-hosted deployments: your data stays on your own server, sensitive fields are encrypted at rest, and AI only organizes and explains information — final judgment always belongs to you and your doctors.

---

## ✨ Features

### 📊 Data Capture & Understanding
| Feature | Description |
|---------|-------------|
| 🔍 **OCR index extraction** | PaddleOCR recognition → LLM table parsing → LLM matching against the standard library, saved automatically; three flows (lab / exam / pathology) routed by report category; manual review & correction |
| 📷 **Image report management** | 27 report categories, upload dedup checks, SSE live progress, thumbnail timeline |
| 🤖 **AI lab interpretation** | Overall assessment + abnormal-indicator explanations + trend changes + suggestions; follow-up reminders auto-created from interpretation results |

### 🗂️ Unified Health Record
| Feature | Description |
|---------|-------------|
| 🧑‍⚕️ **Patient management** | Multi-patient support; name / phone / ID card encrypted with Fernet + one-way hash index for dedup; PHI-edit audit logging |
| 📈 **Treatment timeline** | Unified aggregation across 5 tables, milestones, multi-dimensional filters, date-range statistics |
| 💊 **Medication & adherence** | Medication CRUD (incl. discontinue), intake check-ins (taken/skipped/missed), adherence stats (7–365 days) |
| ⏰ **Follow-up reminders** | Manual / AI-interpretation / consultation sources, pending → sent → confirmed loop |
| 🧪 **Combined indicator queries** | Related indicators aligned by date for side-by-side reading, one click to trend chart |
| 🔎 **Global search** | Fuzzy search across labs / exams / pathology / medication / timeline |

### 🤝 Consultation & Knowledge
| Feature | Description |
|---------|-------------|
| 🏛️ **Virtual consultation (AgentTeams)** | Aggregates records into a consultation prompt; the external AgentTeams project runs the multi-agent consultation, displayed via embedded iframe, with history and session sharing fully preserved |
| 📚 **Knowledge base** | Category tree, document upload/download/preview/search, access logs; txt/pdf/office/images |
| 📤 **Export & sharing** | PDF export for lab reports / timeline / full record (Chinese fonts built in); ShareToken time- and count-limited sharing |

### ⚙️ Platform
| Feature | Description |
|---------|-------------|
| 📱 **Responsive dual layout** | Mobile-first with Vant 4, adaptive desktop layout |
| 🛡️ **Dashboard** | Current medications / abnormal indicators / pending OCR / running consultations / due follow-ups at a glance |
| 👨‍💼 **Admin console** | User management, index-library CRUD / drag-sort / bulk import, index-category management |
| 🔐 **Security stack** | JWT + SSO single-session login, login-failure lockout (Redis Lua), SlowAPI rate limiting, DOMPurify XSS protection, path-traversal protection |

---

## 📸 Screenshots

> All screenshots are generated from the current frontend using fixed fictional demo data. Names, phone numbers and ID numbers are masked and carry a "demo data · desensitized" marker; no real patient data is included. See the [screenshot maintenance guide](docs/screenshots/README.md) (Chinese).

<div align="center">

**Home indicator list** — report counts, abnormal items, todos and grouped indicators in one workspace

![Home indicator list](docs/screenshots/desktop-home-indicators-list.png)

**Lab report detail** — raw values, abnormal status, reference ranges and AI interpretation on one page

![Lab report detail](docs/screenshots/desktop-lab-report.png)

</div>

<details>
<summary><b>📁 More screenshots (exam / pathology / combined indicators / consultation / knowledge base / mobile)</b></summary>

<div align="center">

**Exam report** — findings, diagnostic opinion and follow-up hints in one view

![Exam report](docs/screenshots/desktop-exam-report.png)

**Pathology report** — diagnosis, histology, IHC and gene testing structured together

![Pathology report](docs/screenshots/desktop-pathology-report.png)

**Combined indicator table** — related indicators aligned by date for easy comparison

![Combined indicator table](docs/screenshots/desktop-indicator-comparison-table.png)

**Combined indicator trends** — pick one or two indicators and jump straight to the trend chart

![Combined indicator trends](docs/screenshots/desktop-indicator-comparison-chart.png)

**Virtual consultation workspace** — aggregates records and hosts the AgentTeams multi-agent process

![Virtual consultation workspace](docs/screenshots/desktop-consultation-room.png)

**Knowledge base** — categories, search, summaries and previews for care documentation

![Knowledge base](docs/screenshots/desktop-knowledge-base.png)

**Mobile**

<p>
<img src="docs/screenshots/mobile-home.png" width="19%" alt="Mobile home" />
<img src="docs/screenshots/mobile-lab-report.png" width="19%" alt="Mobile lab report" />
<img src="docs/screenshots/mobile-indicator-comparison.png" width="19%" alt="Mobile combined indicators" />
<img src="docs/screenshots/mobile-consultation.png" width="19%" alt="Mobile consultation" />
<img src="docs/screenshots/mobile-knowledge-base.png" width="19%" alt="Mobile knowledge base" />
</p>

</div>

</details>

---

## 🏗️ Tech Stack & Architecture

### Backend
| Category | Choice |
|----------|--------|
| Framework | FastAPI 0.109+ |
| ORM | SQLAlchemy 2.0 (Async) |
| Database | PostgreSQL 17 + pgvector extension |
| Cache / locks / sessions | Redis 7 |
| AI | OpenAI-compatible LLM API (interpretation / OCR parsing); virtual consultations are executed by the integrated AgentTeams project |
| OCR | PaddleOCR 3.x (CPU by default, optional NVIDIA GPU) + LLM (OpenAI-compatible API) |
| Async jobs | Celery + Redis (follow-up reminder scheduling) |
| Security | Fernet encryption (PHI fields at rest), bcrypt, JWT |
| Rate limiting | SlowAPI |
| PDF export | Playwright/Chromium + Jinja2 templates |
| LLM JSON parsing | In-house `utils/llm_parser.py` (3 strategies + CJK punctuation normalization) |

### Frontend
| Category | Choice |
|----------|--------|
| Framework | Vue 3.4 (Composition API) |
| UI library | Vant 4.9 |
| State management | Pinia |
| Routing | Vue Router 4 |
| Build tool | Vite 8 |
| Charts | ECharts 6 (on-demand imports) |
| Security | DOMPurify (XSS sanitization before v-html) |
| Export | html2canvas + jsPDF + html2pdf.js |
| Markdown | marked + highlight.js |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  Frontend (Vue 3 + Vant)                         │
│  Login / Home(dashboard) / Timeline / Consultation(AgentTeams)   │
│  AI interpretation / Image reports(OCR) / Indicators / Meds ...  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP/REST + SSE
┌───────────────────────────────▼─────────────────────────────────┐
│              API Gateway (FastAPI, 30 route modules)             │
│  Auth / Users / Patients / Medical / Consultation / Timeline     │
│  Medications / Intake logs / Follow-ups / Dashboard / Export     │
│  Sharing / Search / Files / Image reports / KB / Prompts ...     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                 Service Layer (Business Logic)                   │
│  AgentTeamsStartService / AgentTeamsConfigService               │
│  MedicalPromptBuilder / LLMService / InterpretationService      │
│  OCR integration (7 sub-services) / TimelineAggregator          │
│  ExportService / StorageService / EncryptionService             │
│  SessionService / Desensitization / LockService                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                          Data Layer                              │
│  PostgreSQL 17 (primary store)  │  Redis 7 (cache/locks/sessions)│
│  OpenAI-compatible LLM API      │  AgentTeams (external consults)│
│  Local file storage             │  Playwright/Chromium (PDF)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Docker)

The fastest way is Docker Compose.

### 1️⃣ Clone & configure

```bash
git clone https://github.com/nickzhang1102/oncopath.git
cd oncopath
cp .env.example .env
```

Edit `.env` and **fill in these 5 required variables** (adjust the rest as needed):

| Variable | Description | How to generate |
|----------|-------------|-----------------|
| `SECRET_KEY` | JWT signing key, ≥32 chars; startup refuses default values | `openssl rand -hex 32` |
| `DB_PASSWORD` | PostgreSQL password | Choose a strong password |
| `REDIS_PASSWORD` | Redis password | Choose a strong password |
| `ENCRYPTION_KEY` | Fernet key for PHI field encryption (required in production) | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `LLM_API_KEY` | OpenAI-compatible LLM API key used for local AI interpretation and knowledge-base summaries | Your LLM provider console |

> Fill in the remaining LLM settings (`LLM_API_BASE` / `LLM_MODEL_NAME` / `OCR_LLM_API_KEY` / `OCR_LLM_API_BASE` / `OCR_LLM_MODEL_NAME`) according to your OpenAI-compatible provider. AgentTeams uses its own backend integration config — see [`docs/deployment/agentteams-integration.md`](./docs/deployment/agentteams-integration.md) (Chinese).

### 2️⃣ Start services

```bash
docker compose up -d
docker compose ps
```

Port mapping (matches `docker-compose.yml`):
- **Frontend**: binds host `127.0.0.1:3000` → container `80` (Nginx) by default
- **Backend API / PostgreSQL / Redis**: internal Docker network only, no host ports published

To expose the frontend on your LAN, set `FRONTEND_BIND_ADDRESS=0.0.0.0` explicitly; in production keep loopback and terminate HTTPS on a host reverse proxy.

### 3️⃣ Database initialization

On startup the backend container automatically runs `alembic upgrade head` to create/upgrade the schema, then an idempotent seed script creates the default admin, index categories and standard indicators. `agentteams-launch-worker` starts after the backend becomes healthy and does not run migrations. The default admin account is `admin`; its password comes from the `ADMIN_INITIAL_PASSWORD` env var, falling back to `admin123` (**in production always set `ADMIN_INITIAL_PASSWORD` and change it immediately after first login**).

### 4️⃣ Access

- Frontend: http://localhost:3000
- API health check: http://localhost:3000/api/v1/health

---

## 💻 Local Development

### Prerequisites

- Python 3.11 (same as the backend image; a dedicated virtualenv is recommended)
- Node.js 20.19+ or 22.12+
- PostgreSQL 17 (with pgvector extension)
- Redis 7+
- Docker & Docker Compose (optional, to bring up PG / Redis)

### Database setup

1. Create an empty database `medical_report`:
   ```sql
   CREATE DATABASE medical_report;
   ```
2. Run the Alembic public baseline to create tables and stamp the schema version.
3. Run `init_fresh_db.py` to load idempotent seed data (see backend steps below).

### Backend

```bash
cd back

# 1. Prepare env vars (copy the template into back/ because config.py resolves env_file=".env"
#    relative to the working directory)
cp ../.env.example .env
#   Edit back/.env with your local PostgreSQL / Redis / LLM config:
#   - DB_HOST=localhost / DB_PORT=5432 (direct local connection)
#   - REDIS_HOST=localhost / REDIS_PORT=6379
#   - Generate SECRET_KEY / ENCRYPTION_KEY / LLM_API_KEY as described above

# 2. Create/upgrade schema, then load idempotent seed data
alembic upgrade head
python scripts/init_fresh_db.py

# 3. Start the dev server
uvicorn app.main:app --reload --port 8000
```

> For scheduled follow-up reminder jobs, run Celery worker and beat in another terminal:
> ```bash
> cd back
> celery -A app.core.celery_app worker --loglevel=info
> celery -A app.core.celery_app beat --loglevel=info
> ```

### Frontend

```bash
cd front
npm install
npm run dev
# Open http://localhost:3000
```

> The frontend dev server listens on port 3000 by default; make sure `.env` includes it in `CORS_ORIGINS` (the template already does).

---

## 🔌 API Overview

The backend has 30 route modules registered centrally in `app/routers.py`. When running the backend locally you can browse the full endpoint definitions in [Swagger UI](http://localhost:8000/docs); the Docker production deployment does not publish the backend port to the host.

<details>
<summary><b>📋 Route module list</b></summary>

| Module | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Register, login (single-session), token refresh, logout |
| Users | `/api/v1/accounts` | Profile, password change, privacy settings, notification CRUD |
| Patients | `/api/v1/patients` | Patient CRUD, encryption + hash dedup, masked details, PHI edit audit, primary-patient switch, timeline/stats/consultations |
| Consultation | `/api/v1/consultation` | AgentTeams availability, external consultation launch, external session mappings, history details |
| Medical | `/api/v1/medical` | Lab/exam/pathology/record CRUD, standard index library, favorites, abnormal indicators |
| Timeline | `/api/v1/timeline` | Timeline event CRUD, statistics |
| Medications | `/api/v1/medications` | Medication CRUD, discontinue |
| Intake logs | `/api/v1/medication-logs` | Check-in records, today's tasks, adherence stats |
| Follow-ups | `/reminders` | Reminder CRUD, confirm recheck |
| Dashboard | `/api/v1/dashboard` | Home aggregation |
| Export | `/export` | Lab report / timeline / full-record PDFs |
| Sharing | `/share` | Share-token generation and access |
| Search | `/search` | Cross-module global search |
| Files | `/files` | Local file service (authenticated) |
| Image reports | `/api/v1/image_reports` | Image report CRUD, upload (background OCR / SSE progress), dedup checks |
| Knowledge base | `/api/v1/knowledge` | Category tree, document CRUD, search |
| Prompts | `/api/v1/prompt` | Per-patient AI prompt configuration |
| Upload | `/api/v1/upload` | Report image upload and status polling |
| Indicator history | `/api/v1/indicator-history` | Indicator trends (up/down/stable computed) |
| Admin | `/api/v1/admin` | User management, index CRUD/sort/bulk import, category management (admin role required) |

</details>

> All endpoints require authentication by default (except explicitly public ones such as login/register/share links). Rate limits: consultation 5/min, login 5/min, upload 10/min, default 100/min.

---

## 🧪 Testing

The backend uses pytest + pytest-asyncio, covering unit, API, database-baseline and integration scenarios.

```bash
cd back
conda activate oncopath

# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=html

# Unit tests only
pytest tests/ -v -k "not integration"

# Integration tests only
pytest tests/integration/ -v
```

> Tests require a reachable test PostgreSQL database and Redis. AgentTeams consultation integration tests can be run following `docs/testing/agentteams-consultation.md` (Chinese).

---

## 🛳️ Production Deployment

Production deployment follows `docker-compose.yml`. Before deploying, verify every mandatory item in the [Security](#security) section:

PaddleOCR uses CPU by default. NVIDIA GPU environments additionally need `docker-compose.gpu.yml` and the NVIDIA Container Toolkit preinstalled; hardware requirements, full commands, verification, switching and troubleshooting are documented in the [PaddleOCR CPU / NVIDIA GPU deployment guide](./docs/deployment/ocr-cpu-gpu.md) (Chinese).

- Change `SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD`, `ENCRYPTION_KEY`, `LLM_API_KEY` in `.env`
- Set `ADMIN_INITIAL_PASSWORD` to a strong password and change the admin password right after first login
- Restrict `CORS_ORIGINS` to your actual frontend domains
- Keep `ALLOW_UNENCRYPTED_PHI=false` (`ENCRYPTION_KEY` is mandatory in production)
- Configure HTTPS (uncomment the 443 block in the frontend service of `docker-compose.yml` with SSL certs, or terminate TLS on an external reverse proxy)
- Firewall rules: only 80/443 exposed
- Keep `FRONTEND_BIND_ADDRESS=127.0.0.1`, publishing 80/443 through the host reverse proxy
- Schedule regular PostgreSQL backups

```bash
# Production start
docker compose --env-file .env up -d

# The backend entrypoint migrates the schema and loads seed data automatically
```

---

## 🔒 Security

### Data security
- **PHI encryption at rest**: patient name, phone, ID card and other sensitive fields are encrypted with Fernet; the ID card number also gets a one-way SHA-256 hash index for dedup.
- **Password storage**: bcrypt hashes.
- **PHI access audit**: editing endpoints that touch plaintext PHI write audit logs; list/detail endpoints return masked data.

### Authentication & authorization
- **JWT + SSO single-session login**: SessionService manages sessions in Redis — a new login kicks the old session offline and blacklists its token.
- **Login failure lockout**: 5 attempts / 15 minutes via atomic Redis Lua scripts.
- **Admin console**: every `/api/v1/admin` endpoint requires the admin role.

### API & runtime security
- **Auth by default**: all endpoints require authentication except explicitly public ones.
- **Rate limiting**: SlowAPI — login 5/min, consultation 5/min, upload 10/min, default 100/min.
- **SQL injection protection**: parameterized SQLAlchemy ORM queries.
- **XSS protection**: DOMPurify sanitization before any v-html rendering.
- **Path traversal protection**: StorageService validates resolved paths against escaping the storage root.

### Mandatory production checklist

| Item | Requirement |
|------|-------------|
| `SECRET_KEY` | Strong random value from `openssl rand -hex 32`; startup rejects defaults |
| `DB_PASSWORD` / `REDIS_PASSWORD` | Strong passwords |
| `ENCRYPTION_KEY` | Generated via `Fernet.generate_key()`; **if PHI was encrypted with an older key, rotation requires decrypting with the old key first, then re-encrypting with the new one** |
| `ADMIN_INITIAL_PASSWORD` | Strong password; change again immediately after first login |
| `CORS_ORIGINS` | Restricted to real frontend domains — no wildcards |
| `ALLOW_UNENCRYPTED_PHI` | Keep `false` |

---

## 🗺️ Roadmap

- [ ] WeChat OAuth login
- [ ] Migrate tokens to httpOnly cookies + CSRF protection
- [ ] Complete in-browser PDF / Office preview for the knowledge base
- [ ] Frontend unit tests and E2E coverage
- [ ] English UI (i18n)

---

## ⚠️ Medical Disclaimer

**The AgentTeams virtual consultation entry, lab-result interpretation, OCR recognition and similar features are intended solely for organizing health information and assisting understanding and analysis. They do not constitute medical diagnosis or treatment advice, are not a medical device, and cannot replace the professional judgment of a licensed physician.** This system must not be used for medical emergencies. Verify all system output yourself and consult a qualified physician. Any consequences arising from use of this system are borne by the user. See [DISCLAIMER.md](./DISCLAIMER.md) (Chinese).

---

## 📄 License

This project is open source under the [Apache License 2.0](./LICENSE). Third-party dependencies and image assets retain their respective licenses — see [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).

Copyright © 2026 nickzhang1102

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) (Chinese) for the full fork → branch → commit → PR workflow and coding standards.

---

## ☕ Sponsorship

<div align="center">

If OncoPath has helped you, consider buying the author a cup of coffee ☕

**Every bit of support keeps this project going — it truly matters!**

<table>
<tr>
<td align="center"><b>💚 WeChat</b></td>
<td align="center"><b>💙 Alipay</b></td>
</tr>
<tr>
<td><img src="docs/screenshots/wechat.jpg" width="260" alt="WeChat reward QR code" /></td>
<td><img src="docs/screenshots/alipay.jpg" width="260" alt="Alipay QR code" /></td>
</tr>
</table>

A ⭐ star is equally appreciated — it helps more people find this project.

</div>
