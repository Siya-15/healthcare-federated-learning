# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A prototype for a healthcare federated-learning project with five objectives (see `ML/ML_handoff.md` for the authoritative spec):

- **A** — Atypical / emerging symptom detection (`ML/emerging_symptoms/`)
- **B** — Outbreak detection & surveillance (`ML/outbreak_detection/`)
- **C** — Federated learning across 10 simulated hospitals (`ML/federated_learning/`)
- **D** — Structured local clinical database in PostgreSQL (`database*.py`, `loader.py`, `datasets/`)
- **E** — AI treatment advisor (`ML/treatment_advisor/`)

Plus privacy/pseudonymization utilities (`ML/privacy/`). There is no backend or frontend yet — `ML/ML_handoff.md` defines the API surface and integration rules those teams are expected to build.

## Setup you must do before anything runs

1. **`config.py` at the repo root** (gitignored, not in the tree). `database.py` does `from config import DB_CONFIG`, where `DB_CONFIG` is a dict with keys `user`, `password`, `host`, `port`, `database`. Every DB-connected script imports this transitively.
2. **A running PostgreSQL instance** with the schema already created. The schema is not in this repo — only the data that goes into it. Tables include `patient_encounter`, `encounter_symptoms`, `encounter_treatments`, `encounter_complications`, and the master/mapping tables listed in `loader.py`'s `TABLES`.
3. **Dependencies**: `pip install -e ML` (deps are declared in `ML/pyproject.toml` — flwr, torch, pytorch-tabnet, sklearn, pandas, sqlalchemy, psycopg2-binary, python-dotenv). There is no `requirements.txt`.
4. `datasets/knowledge tables/import_tables.py` is the odd one out — it uses `python-dotenv` and env vars `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` (default DB name `federatedProject_db`) instead of `config.py`. Keep the two credential sources pointed at the same database.

## The end-to-end data pipeline

```
datasets/knowledge tables/*.csv        (hand-authored clinical knowledge base)
        │  datasets/knowledge tables/import_tables.py   (one table at a time — edit the
        │                                                hardcoded filename/table name per run)
        ▼
PostgreSQL master + mapping tables
        │  run_multihospital_simulation.py   (simulates 10 hospitals × N days of encounters)
        ▼
PostgreSQL patient_encounter + encounter_* tables
        │  prepare_ml_data.py   (joins encounters + symptoms, one-hot encodes 27 symptoms,
        │                        writes ml_data_H001.csv … ml_data_H010.csv to the CWD)
        ▼
ml_data_H0XX.csv   (per-hospital ML datasets — 20 base cols + 27 binary symptom cols)
        │
        ▼
ML/ modules: federated_learning, emerging_symptoms, outbreak_detection,
             local_models, treatment_advisor, privacy
```

**CSV duplication**: `ml_data_H0XX.csv` exists identically at the repo root *and* in `ML/`. `prepare_ml_data.py` writes to the CWD, and consumer scripts read `ml_data_{id}.csv` relative to the CWD. When you regenerate the datasets, refresh both locations (or run each script from the directory it expects).

## Running things

There is **no test framework, linter, or build step**. The `test_*.py` files at the repo root and in `models/` are standalone verification scripts, not `pytest` — run them directly with `python`. Most need a populated database.

| Command | Run from | Needs |
|---|---|---|
| `python test_loader.py` | repo root | DB with master tables |
| `python test_disease_hospital.py` | repo root | DB (checks per-hospital non-IID disease mix) |
| `python test_100_encounters.py` | repo root | DB (distribution sanity check, no writes) |
| `python test_pipeline.py` | repo root | DB (generates 5 encounters, prints them) |
| `python test_database_writer.py` | repo root | DB (generates + **writes** 10 encounters) |
| `python run_multihospital_simulation.py` | repo root | DB (bulk generate + write; edit `START_DATE` / `NUMBER_OF_DAYS` in-file) |
| `python prepare_ml_data.py` | dir where you want the CSVs | DB with encounters |
| `flwr run .` | `ML/` | `ml_data_H0XX.csv` present in `ML/` |
| `python -m outbreak_detection.outbreak_detection` etc. | `ML/` | DB and/or CSVs depending on module |

**Working-directory gotcha for `ML/` scripts**: DB-connected ML modules (`treatment_advisor`, `outbreak_detection`, `privacy`) do `sys.path.append(<parent of ML/>)` then `from database import get_engine`, so `database.py` + `config.py` must be importable — run them with the repo root on `PYTHONPATH`. CSV-only modules (`local_models`, `emerging_symptoms`, `federated_learning`) instead need the `ml_data_*.csv` files in the CWD. `treatment_advisor.py` loads `treatment_success_model.pkl` by bare filename — run it from `ML/models/` or adjust the path.

## Simulation architecture (`simulation/`, `generators/`, `models/`)

`SimulationEngine.generate_patient(context)` runs a **fixed ordered pipeline** of generators, each mutating one shared `Encounter` dataclass (`models/encounter.py`):

```
encounter → demographics → disease → severity → symptom → symptom_onset
          → vitals → treatment → complication → outcome
```

Order matters — later generators read fields set by earlier ones (e.g. `DiseaseGenerator` uses `demographics.age`; `SeverityGenerator` uses the disease). All generators are constructed with the `tables` dict from `loader.load_all_tables()` (except `EncounterGenerator`, `SymptomOnsetGenerator`, `OutcomeGenerator`).

`SimulationContext` carries the per-day state: `current_date`, `hospital_id`, `season` (`"Summer"` / `"Monsoon"` / `"Winter"`), `outbreak_active`, `outbreak_disease`.

**`DiseaseGenerator` deliberately produces non-IID data.** It starts from base prevalence weights (`disease_generation_config`) then applies multiplicative rules for hospital (`self.hospital_rules`, hardcoded per `H001`–`H010`), age group, season, and active outbreak (×3). This per-hospital skew is what makes the federated-learning demo meaningful — don't "fix" it into a uniform distribution.

`DatabaseWriter.save(encounter)` writes one encounter across all four `encounter*` tables in a single transaction, translating the model's enums into the DB's expected string values (e.g. `outcome` `"Recovered"/"Not Recovered"/"Critical"` → `discharge_status` `"Recovered"/"Stable"/"Referred"`).

## Federated learning (`ML/federated_learning/`)

Flower app (entry points in `ML/pyproject.toml` → `[tool.flwr.app.components]`), invoked with `flwr run` from `ML/`. TabNet multi-label classifier, FedAvg, 3 server rounds (`num-server-rounds`), 27 symptom labels, 10 hospital clients.

- `task.py` — `FEATURE_COLUMNS` (10 vitals/demographic inputs), `TARGET_COLUMNS` (27 symptoms), feature prep, per-hospital CSV load with an 80/20 split.
- `model_utils.py` — TabNet construction and parameter get/set helpers.
- `flower_client.py` — hospital-side client; `get_hospital_id(context)` maps Flower `node_id % 10` → `H001`–`H010`. Raw CSV rows never leave the client; only model parameters are returned.
- `flower_server.py` — coordinates rounds and FedAvg aggregation.

The `[tool.flwr.federations]` block is commented out (migration notice) — supply the federation another way if `flwr run .` complains.

## Ground rules from `ML/ML_handoff.md`

- The ML layer is **frozen for Review 2** — the remaining work is backend/frontend integration, not new algorithms. Don't add differential privacy, secure aggregation, FedProx, transformers, SHAP, etc.; the handoff lists those explicitly as future work not to present as done.
- Report FL metrics **honestly**: validated run was Accuracy 87.82%, Micro-F1 39.23%, Macro-F1 5.83%, Hamming loss 12.18% — Macro-F1 is low and Micro-F1 did not improve monotonically.
- Frontend must never touch PostgreSQL or Python ML modules directly — everything goes through a backend API.
- Use `patient_token` / pseudonyms in any application-facing view; never surface raw `patient_id`.
- Surveillance outputs stay aggregated (hospital-level, cross-hospital, pattern-level), never individual patient rows. Alert levels: GREEN / YELLOW / ORANGE / RED.
- The treatment advisor is decision support, not autonomous prescription.
