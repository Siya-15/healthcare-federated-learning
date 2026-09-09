# Healthcare Backend — Live Objective Integration

This backend is a replacement for the previous snapshot/heuristic-heavy backend.

## Data source

FastAPI and the ML-side database utilities can use the same Supabase PostgreSQL database.
Keep the real `.env` outside Git.

## Objective integration

- **A:** exposes the project's generated Objective A ML outputs (`advanced_symptom_novelty.csv`, fusion and cross-hospital artifacts). The current A implementation is artifact/file based, so the API does not claim request-time retraining.
- **B:** calls the actual `run_foundation()` functions over the current database, rather than `dashboard_snapshot` values.
- **C:** reports the actual Flower/FedAvg implementation and local-node dataset status. Differential privacy and secure aggregation remain explicitly NOT IMPLEMENTED.
- **D:** queries the live Supabase PostgreSQL tables.
- **E:** executes the actual E1-E13 modules. No heuristic probability/recovery/risk/SHAP replacement is used.

## Important E model artifacts

The E6/E7/E8 artifacts are expected at the project root, as required by the ML modules. E9 is loaded from the treatment-advisor package path. Do not invent missing artifacts.

## Key routes

- `/api/objectives/a`
- `/api/objectives/b`
- `/api/objectives/c`
- `/api/objectives/d`
- `/api/objectives/e/{encounter_id}`

Existing portal routes under `/api/clinical`, `/api/surveillance`, `/api/federated`, `/api/privacy`, and `/api/models` remain available.
