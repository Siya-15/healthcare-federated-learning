# Running the backend API

FastAPI service that backs the multi-portal frontend. It owns the Supabase
schema, serves every `/api/*` endpoint the React app calls, and enforces RBAC +
hospital scope server-side.

## 1. Prerequisites

- The repo `.venv` (Python 3.12). Everything needed is already installed; to
  recreate: `.venv/bin/pip install -r backend/requirements.txt`.
- A `.env` at the repo root with a Supabase / PostgreSQL URL:

  ```
  DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require"
  # optional
  PRIVACY_SECRET="something-long-and-secret"     # pseudonymisation salt
  ADVISOR_ENGINE=auto                            # auto | ml | heuristic
  BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
  ```

  The password must be URL-encoded. No credentials live in source.

## 2. Create the schema + load seed data

```
.venv/bin/python backend/seed_supabase.py            # migrate + seed (idempotent)
.venv/bin/python backend/seed_supabase.py --schema   # apply migration only
.venv/bin/python backend/seed_supabase.py --reset    # drop app tables, then migrate + seed
```

This applies `backend/migrations/002_supabase_app_schema.sql` and loads:

- reference data — 10 hospitals, 9 diseases, 3 severities, 27 symptoms, 14 treatments;
- advisor config — `disease_treatment_mapping` (E2), `treatment_contraindication`
  (E3), `treatment_config` per hospital (E4);
- encounters — 5 canonical sample records (tokens the UI references) + 40
  synthetic ones (~4 per hospital) for the history / dashboard views;
- `dashboard_snapshot` — 14 JSONB payloads for the Surveillance / Federated /
  Privacy / AI-Ops portals, shaped exactly like the API responses.

## 3. Run the server

```
.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
```

- Interactive docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

## 4. Point the frontend at it

```
cd frontend
npm run dev:live          # = VITE_USE_MOCK=0 vite
```

`npm run dev` (mock mode) still works with no backend. In live mode the Vite dev
server proxies `/api/*` to `127.0.0.1:8000`; a pure connection failure falls back
to a fixture, but real 403 / 404 / 422 / 503 responses surface in the UI.

Switch the demo identity with the role / hospital selectors in the top bar —
those set the `X-Demo-Role` / `X-Demo-Hospital` headers the backend authorises
against.

## 5. Endpoints

| Method · Path | Roles | Source |
|---|---|---|
| `GET /api/health` | any | liveness + DB ping |
| `GET /api/clinical/form-options` | DOCTOR | master tables |
| `GET /api/clinical/dashboard` | DOCTOR | `doctor.dashboard` snapshot + live counts |
| `GET /api/clinical/encounters` | DOCTOR | `patient_encounter` (own hospital) |
| `GET /api/clinical/encounters/{id}` | DOCTOR | `patient_encounter` (+ scope check) |
| `POST /api/clinical/encounters` | DOCTOR | writes `patient_encounter` + symptoms |
| `GET /api/clinical/treatment-advisor/{id}` | DOCTOR | E1–E13 for a stored encounter |
| `POST /api/clinical/treatment-advisor` | DOCTOR | E1–E13 for a submitted context |
| `GET /api/surveillance/{overview,alerts,emerging-symptoms,trends}` | HOSPITAL_ADMIN, PUBLIC_HEALTH_ADMIN, TECH_REVIEWER | `surveillance.*` snapshots |
| `GET /api/federated/{network,rounds,model}` | HOSPITAL_ADMIN, PUBLIC_HEALTH_ADMIN, TECH_REVIEWER | `federated.*` snapshots |
| `GET /api/privacy/{policy,data-flow,audit}` | HOSPITAL_ADMIN, PUBLIC_HEALTH_ADMIN, TECH_REVIEWER | `privacy.*` snapshots |
| `GET /api/models/{overview,metrics,versions}` | PUBLIC_HEALTH_ADMIN, TECH_REVIEWER | `models.*` snapshots |
| `GET /api/models/explanations/{encounter}/{treatment}` | DOCTOR (own encounter) or TECH_REVIEWER | E11 attribution |

## 6. Treatment-advisor engine

`ADVISOR_ENGINE` controls how `/treatment-advisor` is served:

- `auto` (default) — try the ML `ML/treatment_advisor` pipeline; if it can't run
  (no model artifacts, encounter not persisted with the ML schema, heavy deps
  missing), fall back to the heuristic engine.
- `ml` — require the ML pipeline; return `503` if unavailable.
- `heuristic` — always use the heuristic engine.

The **heuristic engine** (`app/services/advisor_engine.py`) is not a model and
not a re-implementation of E1–E12. It runs the real E2/E3/E4 config from the
database (candidate mapping, contraindications, per-hospital availability) and
applies transparent project-defined arithmetic for the E6–E12 numbers. Every
response is labelled `engine: "heuristic_fallback"` and carries the standard
"decision support only, not clinically validated" disclaimer. The E12 ranking
weights live in Python and are the single source of truth for the UI.

## 7. What is NOT implemented (honestly)

- Differential privacy / secure aggregation — surfaced as `NOT_IMPLEMENTED`.
- FL metrics are the validated honest numbers (Macro-F1 ≈ 0.058).
- Surveillance / federated / privacy / model payloads are stored prototype
  outputs, not live recomputation.
- `POST /api/clinical/encounters` persists to the app schema; it does not run the
  full simulation generator pipeline.
