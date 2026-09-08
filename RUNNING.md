# Running the application

The application layer is a **React + Vite + Tailwind** frontend covering all four
portals from the integration spec — **Doctor**, **Surveillance**, **Federated &
Privacy**, **AI Operations** — talking to FastAPI over `/api` only (it never
imports the Python ML modules or downloads a model artifact).

- **Frontend** (`frontend/`): built on this branch. Runs standalone against
  labelled sample data, so you can see every portal now. See
  [`frontend/RUNNING.md`](frontend/RUNNING.md) for the full guide.
- **Backend** (`backend/app/`): built on this branch. FastAPI service that serves
  the whole `/api/*` contract from a Supabase / PostgreSQL schema and enforces
  RBAC + hospital scope server-side. Full guide in
  [`backend/RUNNING.md`](backend/RUNNING.md); the essentials are below.

Run the frontend alone for a quick look; run both for the live application.

## Frontend — quick start

Use **Node 18+**. Dependencies are vendored in `frontend/node_modules`;
`npm install` only reconciles them with `package.json`.

```bash
cd frontend
npm install          # optional the first time; deps are already present
npm run dev          # http://localhost:5173
```

Open **http://localhost:5173** — it lands on a portal picker for the current
demo role.

### Sample-data mode (the default — no backend)

The service layer (`src/services/*.js`) calls `/api/...`. With no backend it
resolves **labelled fixtures** (`src/mocks/*.js`) and every screen shows a blue
"Sample data" banner. Nothing shown is a real patient, hospital, or model result.

- Switch portal/role with the top-bar **DEMO Role** selector (persisted).
- Pick the acting hospital with the top-bar **Hospital** selector (doctor /
  hospital-admin roles).
- New Encounter → *Analyze* runs a deterministic sample `E1–E12`; changing
  severity / SpO₂ / age visibly moves the ranked output (demo step 6).
- Run against the real backend: `npm run dev:live` (`VITE_USE_MOCK=0`) — see the
  Backend section below. In live mode a real `403 / 404 / 422 / 503` is shown as
  an error; only a connection failure falls back to fixtures.

### Build a static bundle

```bash
cd frontend && npm run build && npm run preview   # http://localhost:4173
```

Output goes to `frontend/dist/` (git-ignored).

## Portals & roles

| Role | Portals | Key screens |
|---|---|---|
| Doctor / Clinician | Doctor | Dashboard · New Encounter · Treatment Advisor (E1–E13) · History |
| Hospital Administrator | Surveillance, Federated & Privacy | Overview · Alerts · Emerging Symptoms · Trends · FL rounds · Data flow · Privacy audit |
| Central / Public-health Admin | Surveillance, Federated & Privacy, AI Operations | + Model overview · Metrics · Versions · SHAP explanations |
| Technical Reviewer / Admin | Surveillance, Federated & Privacy, AI Operations | same as above |

RBAC is enforced server-side in production (spec section 16); the role switcher
stands in for auth and `RoleGuard` filters navigation + shows an explicit
"access denied" panel.

## Backend — quick start

FastAPI service in `backend/app/`. It owns the Supabase schema, serves every
`/api/*` endpoint the frontend calls, and enforces RBAC + hospital scope from the
`X-Demo-Role` / `X-Demo-Hospital` headers. Full detail:
[`backend/RUNNING.md`](backend/RUNNING.md).

### 1. Prerequisites

- The repo `.venv` (Python 3.12). Deps are already installed; to recreate:
  `.venv/bin/pip install -r backend/requirements.txt`.
- A `.env` at the **repo root** with a Supabase / PostgreSQL URL (password
  URL-encoded; no credentials in source):

  ```
  DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
  # optional
  PRIVACY_SECRET="something-long-and-secret"   # pseudonymisation salt
  ADVISOR_ENGINE=auto                          # auto | ml | heuristic
  ```

### 2. Create the schema + seed data

```bash
.venv/bin/python backend/seed_supabase.py            # migrate + seed  (idempotent)
.venv/bin/python backend/seed_supabase.py --schema   # apply migration only, no seed
.venv/bin/python backend/seed_supabase.py --reset    # DROP app tables, then migrate + seed
```

`seed_supabase.py` applies
[`backend/migrations/002_supabase_app_schema.sql`](backend/migrations/002_supabase_app_schema.sql)
and loads:

- **reference data** — 10 hospitals, 9 diseases, 3 severities, 27 symptoms, 14
  treatments;
- **advisor config** — `disease_treatment_mapping` (E2), `treatment_contraindication`
  (E3), per-hospital `treatment_config` (E4);
- **encounters** — 5 canonical sample records (the `patient_token`s the UI
  references) + 40 synthetic (~4 per hospital) for the history / dashboard views;
- **`dashboard_snapshot`** — 14 JSONB payloads for the Surveillance / Federated /
  Privacy / AI-Ops screens, shaped exactly like the API responses.

Re-running upserts the reference data and regenerates the synthetic encounters
and snapshots. Edit the payloads in `backend/seed_data.py` and re-run to change
what those portals show.

### 3. Run the API

```bash
.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
```

- Interactive docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

### 4. Run the frontend against it

```bash
cd frontend && npm run dev:live        # = VITE_USE_MOCK=0 vite
```

Vite proxies `/api` to `127.0.0.1:8000` (`frontend/vite.config.js`). Switch the
demo identity with the top-bar role / hospital selectors — those set the headers
the backend authorises against. Every treatment-advisor run is persisted to the
`advisor_run` table.

### Endpoints (spec section 7)

```
GET  /api/health
GET  /api/clinical/form-options | dashboard
GET  /api/clinical/encounters                 POST /api/clinical/encounters
GET  /api/clinical/encounters/{id}
GET  /api/clinical/treatment-advisor/{id}     POST /api/clinical/treatment-advisor
GET  /api/surveillance/overview | alerts | emerging-symptoms | trends
GET  /api/federated/network | rounds | model
GET  /api/privacy/policy | data-flow | audit
GET  /api/models/overview | metrics | versions
GET  /api/models/explanations/{encounter}/{treatment}
```

Role access: `clinical/*` → Doctor; `surveillance/*`, `federated/*`, `privacy/*`
→ Hospital Admin / Public-health Admin / Tech Reviewer; `models/*` → Public-health
Admin / Tech Reviewer; `models/explanations/*` → the treating Doctor or a Tech
Reviewer.

### Treatment-advisor engine

`ADVISOR_ENGINE` picks how `/treatment-advisor` runs: `auto` (default) tries the
`ML/treatment_advisor` E1–E12 pipeline and falls back to a DB-config-backed
heuristic engine (`backend/app/services/advisor_engine.py`, labelled
`engine: "heuristic_fallback"`) when model artifacts / ML deps are absent; `ml`
requires the pipeline (503 otherwise); `heuristic` always uses the fallback. E12
weights stay in Python. Differential privacy / secure aggregation remain
`NOT_IMPLEMENTED`; FL metrics are the validated honest numbers.

---

## Not this — the ML / data pipeline

Generating data or retraining (multi-hospital simulation → `prepare_ml_data.py`
→ `flwr run` / the A–B–E analysis modules) is a separate workflow that needs a
`.env` + PostgreSQL. See `CLAUDE.md`. The frontend never triggers it.
