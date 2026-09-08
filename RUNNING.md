# Running the application

The application layer is a **React + Vite + Tailwind** frontend covering all four
portals from the integration spec — **Doctor**, **Surveillance**, **Federated &
Privacy**, **AI Operations** — talking to FastAPI over `/api` only (it never
imports the Python ML modules or downloads a model artifact).

- **Frontend** (`frontend/`): built on this branch. Runs standalone against
  labelled sample data, so you can see every portal now. See
  [`frontend/RUNNING.md`](frontend/RUNNING.md) for the full guide.
- **Backend** (`backend/`): **not built on this branch.** The FastAPI service and
  its `/api/*` endpoints are specified in the integration handoff but not
  implemented here. A different, CSV-backed FastAPI app exists on the
  `feature/keertika` branch (its own `RUNNING.md` covers it).

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
- Run against a real backend later: `VITE_USE_MOCK=0 npm run dev`. In live mode a
  real `403 / 404 / 422 / 503` is shown as an error; only a connection failure
  falls back to fixtures.

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

## Connecting a real backend later

Run FastAPI on `http://127.0.0.1:8000` (Vite proxies `/api` there — see
`frontend/vite.config.js`) exposing, per spec section 7:

```
GET  /api/clinical/dashboard | form-options
GET  /api/clinical/encounters                POST /api/clinical/encounters
GET  /api/clinical/encounters/{id}
GET  /api/clinical/treatment-advisor/{id}    POST /api/clinical/treatment-advisor
GET  /api/models/explanations/{encounter}/{treatment}
GET  /api/surveillance/overview | alerts | emerging-symptoms | trends
GET  /api/federated/network | rounds | model
GET  /api/privacy/policy | data-flow | audit
GET  /api/models/overview | metrics | versions
```

Start the dev server with `VITE_USE_MOCK=0`; no frontend change is needed. Align
real responses to `src/mocks/*` / `src/types/apiSchemas.js` — the fixtures follow
the contract, they don't define it.

---

## Not this — the ML / data pipeline

Generating data or retraining (multi-hospital simulation → `prepare_ml_data.py`
→ `flwr run` / the A–B–E analysis modules) is a separate workflow that needs a
`.env` + PostgreSQL. See `CLAUDE.md`. The frontend never triggers it.
