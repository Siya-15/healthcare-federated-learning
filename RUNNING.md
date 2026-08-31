# Running the prototype

## One-time setup

```bash
# Python 3.12 — NOT the system 3.14, which has no reliable torch wheels
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt

# ML analysis scripts (optional — only needed to regenerate ML/data/*.csv)
.venv/bin/python -m pip install "flwr[simulation]>=1.35.0" pytorch-tabnet torch

cd frontend && npm install && cd ..
```

Note: `pip install -e ML` from CLAUDE.md does not work — `ML/pyproject.toml`
declares no `[tool.setuptools]` packages and the flat layout has several
top-level directories, so setuptools refuses to pick one. Install the
dependency list directly, as above.

## Run

Two terminals.

```bash
# Terminal 1 — API on :8000
.venv/bin/uvicorn backend.app.main:app --reload

# Terminal 2 — UI on :5173
cd frontend && npm run dev
```

Open http://localhost:5173. Interactive API docs: http://localhost:8000/docs

## Data source

The backend reads the **committed CSV artifacts**, not PostgreSQL:

- `ML/ml_data_H001..H010.csv` — 8,845 encounters, all 10 hospitals
- `ML/data/*.csv` — precomputed surveillance, privacy audit, patterns
- `ML/models/treatment_success_model.pkl` — trained RandomForest
- `datasets/knowledge tables/*.csv` — disease / treatment / severity masters

This is because the PostgreSQL schema is not in this repository. It costs
exactly one endpoint: `POST /api/encounters` returns 501, since creating an
encounter needs a database write. Everything else is fully functional.

To switch to Postgres later, replace the loaders in `backend/app/data.py` —
the router layer above them does not change.

## Endpoints

| Endpoint | Status |
|---|---|
| `GET /api/dashboard` | working |
| `GET /api/surveillance` | working |
| `GET /api/federated-learning/status` | working (static artifact — see below) |
| `POST /api/treatment/recommend` | working |
| `GET /api/privacy/status` | working |
| `GET /api/hospitals` | working |
| `GET /api/encounters/{token}` | working |
| `GET /api/encounters` | working (list, filterable) |
| `POST /api/encounters` | **501 — needs the DB schema** |

`GET /api/federated-learning/status` serves
`backend/app/artifacts/fl_run.json`, the record of the last validated run.
Per the integration guide, opening the dashboard must not trigger a live
federated simulation.

## Privacy

Raw `patient_id` and `encounter_id` are never emitted. Every encounter is keyed
by `patient_token`, a deterministic `SHA-256(secret + ":" + id)` pseudonym using
the same scheme as `ML/privacy/privacy_protection.py`.

Set a real secret in production:

```bash
export PRIVACY_SECRET="..."
```

It defaults to `local-hospital-secret` so the prototype runs out of the box.
