# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A prototype for a healthcare federated-learning project with five objectives (see `ML/ML_handoff.md` for the authoritative spec). The ML modules are organized as **numbered pipeline stages** per objective:

- **A** — Atypical / emerging symptom detection (`ML/emerging_symptoms/`, stages **A1–A9**)
- **B** — Outbreak detection & surveillance (`ML/outbreak_detection_parent/outbreak_detection_child/`, stages **B1–B14**)
- **C** — Federated learning across 10 simulated hospitals (`ML/federated_learning/`; **C3** = standardized dataset contract)
- **D** — Structured local clinical database in PostgreSQL (`database.py`, `database_writer.py`, `loader.py`, `datasets/`, `migrations/`)
- **E** — AI treatment advisor (`ML/treatment_advisor/`, stages **E1–E12**)

Plus privacy/pseudonymization utilities (`ML/privacy/`).

### Branch layout — important

The repo has two divergent lines of work off the `ed29318` root commit:

- **`main`** (this branch): the ML + simulation expansion — labs/imaging generators, A1–A9 / B1–B14 / E1–E12 pipelines, `migrations/`, audit scripts. Plus a **multi-portal frontend** (`frontend/`, React + Vite + Tailwind — Doctor / Surveillance / Federated & Privacy / AI Operations portals per the integration spec; see `RUNNING.md` and `frontend/RUNNING.md`). **No backend** — the FastAPI `/api/*` surface the frontend calls (spec section 7) is not implemented here; every screen runs against labelled sample fixtures (`frontend/src/mocks/*.js`) and `frontend/src/services/*` flips to live calls when started with `VITE_USE_MOCK=0`.
- **`feature/keertika`**: a *different*, CSV-backed FastAPI `backend/app/` + an earlier single-page React/Vite `frontend/`, plus the `md_files/` handoff pack. It does **not** have `main`'s ML expansion or the multi-portal UI.

A stray `backend/` directory in the working tree on `main` is a stale leftover from a branch switch (only `__pycache__`) — ignore it. `ML/ML_handoff.md` plus the two integration handoff docs (Objective E architecture; whole-app integration spec) define the API surface the backend team builds against.

**Frontend rules baked into the UI (spec section 16):** treatment-success probabilities are observational associations not causal effects; SHAP is associational metadata; E8/E9 ranges are model-derived predictive spreads not confidence intervals; Objective A shows atypical symptom patterns never "new pathogen"; differential privacy / secure aggregation render as `NOT_IMPLEMENTED`; FL metrics shown honestly (Macro-F1 ≈ 0.058). Keep these when editing pages.

## Setup you must do before anything runs

1. **A `.env` file at the repo root.** All DB access now flows through `python-dotenv`. `config.py` (committed) reads `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` from the environment / `.env` and exposes `DB_CONFIG`; `database.py` does `from config import DB_CONFIG`. `datasets/knowledge_tables/import_tables.py` and `import_lab_tables.py` read the same five env vars directly (default DB name in `import_tables.py` is `federatedProject_db`). One credential source now — keep everything pointed at the same database.
2. **A running PostgreSQL instance with the schema created.** The base schema (table definitions for `patient_encounter`, `encounter_symptoms`, `encounter_treatments`, `encounter_complications`, `encounter_labs`, `encounter_imaging`, and the master/mapping tables in `loader.py`'s `TABLES`) is **not** in this repo. `migrations/001_complete_encounter_persistence.sql` only *adds columns* (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) to the four core `encounter*` tables — it assumes they already exist, and it does not create `encounter_labs` / `encounter_imaging`.
3. **Dependencies**: `pip install -e ML` (deps in `ML/pyproject.toml` — flwr[simulation], torch, pytorch-tabnet, sklearn, pandas, numpy, joblib, sqlalchemy, psycopg2-binary, python-dotenv). There is no `requirements.txt` on this branch.

## The end-to-end data pipeline

```
datasets/knowledge_tables/*.csv        (hand-authored clinical knowledge base:
        │                               disease/symptom/treatment/complication/severity
        │                               + lab + imaging masters and disease_* mappings)
        │  datasets/knowledge_tables/import_tables.py  (one table per run — edit the
        │                                               hardcoded file_path near line 29)
        │  import_lab_tables.py                        (lab/imaging tables; NOTE: its
        │                                               BASE points at the old spaced
        │                                               "datasets/knowledge tables" path
        │                                               and needs fixing to the underscore
        │                                               name before it will run)
        ▼
PostgreSQL master + mapping tables
        │  run_multihospital_simulation.py   (10 hospitals × NUMBER_OF_DAYS of encounters;
        │                                     currently START_DATE 2026-06-01, 90 days)
        ▼
PostgreSQL patient_encounter + encounter_symptoms/treatments/complications/labs/imaging
        │  prepare_ml_data.py   (joins encounters + symptoms, pivots 27 symptoms to binary
        │                        columns, writes ml_data_H001.csv … ml_data_H010.csv to CWD)
        ▼
ml_data_H0XX.csv   (per-hospital ML datasets — base cols incl. visit_timestamp + 27 symptom cols)
        │
        ▼
ML/ modules: federated_learning, emerging_symptoms (A1–A9),
             outbreak_detection_parent/outbreak_detection_child (B1–B14),
             local_models, treatment_advisor (E1–E12), privacy
```

**Two different path conventions coexist — know which you're in:**

- **Older root-level + first-gen ML scripts are CWD-relative and their outputs are committed.** `prepare_ml_data.py` writes bare `ml_data_H0XX.csv` into the CWD; they exist identically at the repo root *and* in `ML/`. Regenerating means refreshing both. First-gen `ML/` analysis scripts also write bare filenames into the CWD while the committed copies live in `ML/data/` — move new output there by hand.
- **The newer numbered-stage ML modules (A3+, most B*, E*) resolve paths via `Path(__file__)`** (`ML_DIR = Path(__file__).resolve().parents[1]`, etc.) and read/write their intermediate CSVs *next to the code* — in `ML/emerging_symptoms/` and `ML/outbreak_detection_parent/outbreak_detection_child/`. Each stage consumes the previous stage's CSV (e.g. A3 `cross_hospital_symptom_patterns.csv` → A4 `emerging_disease_inference.csv` → A5 → A6 → A7 `emerging_signal_fusion.csv`; B10 → B11 `alert_engine.csv` → B12 `explainability_engine.csv`). So the modules must be run in stage order.

`.gitignore` has the "don't version generated datasets" rules commented out deliberately — all generated CSVs, baselines (`ML/emerging_symptoms/baseline_state.json`, `baseline_versions/`), and `ML/models/treatment_success_model.pkl` are checked in.

## Running things

There is **no test framework, linter, or build step.** `test_*.py` files are standalone verification scripts — run them directly with `python`. Most need a populated database.

| Command | Run from | Needs |
|---|---|---|
| `python test_loader.py` | repo root | DB with master tables |
| `python test_disease_hospital.py` | repo root | DB (per-hospital non-IID disease mix check) |
| `python test_100_encounters.py` | repo root | DB (distribution sanity check, no writes) |
| `python test_pipeline.py` | repo root | DB (generates 5 encounters, prints them) |
| `python test_database_writer.py` | repo root | DB (generates + **writes** encounters) |
| `python test_database_roundtrip.py` | repo root | DB (generate → write → read-back verification) |
| `python test_lab_persistence.py` | repo root | DB (labs/imaging persistence check) |
| `python test_daily_hospital.py` | repo root | DB (vitals generator smoke test) |
| `python models/test_encounter.py` | `models/` | nothing — `from encounter import …` only resolves inside `models/` |
| `python run_multihospital_simulation.py` | repo root | DB (bulk generate + write; edit `START_DATE` / `NUMBER_OF_DAYS` in-file) |
| `python prepare_ml_data.py` | repo root | DB with encounters (imports `database`, so root must be importable) |
| `python audit_database.py` / `audit_knowledge.py` | repo root | DB (data-quality / coverage audits — e.g. symptoms never generated) |
| `python inspect_master_data.py` / `list_tables.py` / `inspect_schema.py` / `inspect_all_schemas.py` | repo root | DB (schema/data introspection helpers) |
| `flwr run .` | `ML/` | `ml_data_H0XX.csv` in `ML/`, plus a federation of **≥10 supernodes** |
| `PYTHONPATH=.. python -m outbreak_detection_parent.outbreak_detection_child.<module>` | `ML/` | DB and/or upstream-stage CSVs |
| `PYTHONPATH=.. python -m emerging_symptoms.<module>` | `ML/` | `ml_data_*.csv` and/or upstream-stage CSVs |

**Working-directory rules for `ML/` scripts.** DB-connected modules append the repo root to `sys.path` in varying ways; the reliable invocation is from `ML/` with `PYTHONPATH=..` (or from the repo root with `PYTHONPATH=ML`). CSV-only modules (`local_models`, first-gen `emerging_symptoms`, `federated_learning`) need `ml_data_*.csv` in the CWD. `treatment_advisor/treatment_model.py` and `treatment_advisor.py` load/save `treatment_success_model.pkl` by bare filename (run from `ML/models/`, or adjust); `treatment_recommender.py` resolves it via `ML_DIR`.

`encounter_validator.py` (`EncounterValidator`, raises `EncounterValidationError`) is a library used to sanity-check generated encounters against the loaded `tables` dict — not a runnable script.

## Simulation architecture (`simulation/`, `generators/`, `models/`)

`SimulationEngine.generate_patient(context)` runs a **fixed ordered pipeline**, each generator mutating one shared `Encounter` dataclass (`models/encounter.py`):

```
encounter → demographics → disease → severity → symptom_onset → symptom
          → vitals → lab → imaging → treatment → complication → outcome
```

Order matters — later generators read fields set by earlier ones (`DiseaseGenerator` uses `demographics.age`; `SeverityGenerator` uses the disease; `LabGenerator` / `ImagingGenerator` use the disease + severity). Note `symptom_onset` now runs **before** `symptom`, and `lab` + `imaging` sit between `vitals` and `treatment`. All generators are constructed with the `tables` dict from `loader.load_all_tables()` (except `EncounterGenerator`, `SymptomOnsetGenerator`, `OutcomeGenerator`).

`SimulationContext` carries per-day state: `current_date`, `hospital_id`, `season` (`"Summer"` / `"Monsoon"` / `"Winter"`), `outbreak_active`, `outbreak_disease`.

**What actually drives a run:** `run_multihospital_simulation.py` builds the context inline with `season="Monsoon"` and `outbreak_active=False` hardcoded, over `START_DATE` + `NUMBER_OF_DAYS` (currently 2026-06-01, 90 days) for every hospital in `hospital_master`. So `DiseaseGenerator.apply_season_rules` runs monsoon-only and `apply_outbreak_rules` is a no-op in the committed data — vary the context for seasonal or outbreak data. `simulation/simulation_config.py`'s `SIMULATION_CONFIG` is **imported nowhere**; nothing seeds the RNG, so runs are not reproducible.

**`DiseaseGenerator` deliberately produces non-IID data.** Base prevalence weights (`disease_generation_config`) × multiplicative rules for hospital (`self.hospital_rules`, hardcoded per `H001`–`H010`), age group, season, and active outbreak (×3). This per-hospital skew is what makes the federated-learning demo meaningful — don't "fix" it into a uniform distribution.

`DatabaseWriter.save(encounter)` writes one encounter across all six `encounter*` tables (`patient_encounter`, `encounter_symptoms`, `encounter_treatments`, `encounter_complications`, `encounter_labs`, `encounter_imaging`) in a single transaction, translating the model's enums into the DB's expected strings (e.g. `outcome` `"Recovered"/"Not Recovered"/"Critical"` → `discharge_status` `"Recovered"/"Stable"/"Referred"`). `database_writer_backup.py` is a pre-labs/imaging snapshot kept for reference — not wired to anything.

## Federated learning (`ML/federated_learning/`)

Flower app (entry points in `ML/pyproject.toml` → `[tool.flwr.app.components]`), run with `flwr run` from `ML/`. TabNet multi-label classifier, FedAvg, 3 server rounds, 27 symptom labels, 10 hospital clients.

- `task.py` — `FEATURE_COLUMNS`, `TARGET_COLUMNS` (27 symptoms), feature prep, per-hospital CSV load with 80/20 split.
- `federated_dataset.py` — **C3**: the standardized dataset contract (`FEDERATED_FEATURE_COLUMNS` / target columns / ordering / dtypes / binary encoding / matrix shape) every hospital must match. `validate_all_hospitals_c3.py` checks all 10 CSVs against it.
- `model_utils.py` — TabNet construction and parameter get/set helpers.
- `flower_client.py` — hospital-side client; `get_hospital_id(context)` maps Flower `node_id % 10` → `H001`–`H010`. Raw CSV rows never leave the client; only model parameters are returned.
- `flower_server.py` — coordinates rounds and FedAvg aggregation.

Two config traps:

- `flower_server.py` hardcodes the round count and does not read `num-server-rounds` from `[tool.flwr.app.config]`. Change the round count in the server.
- `FedAvg` sets `min_train_nodes` / `min_evaluate_nodes` / `min_available_nodes` to **10**. `[tool.flwr.federations]` is commented out (migration notice) with reference `num-supernodes = 3` — a federation that small waits forever. Supply ≥10 supernodes.

## ML pipeline stages (numbered modules)

The A/B/E modules are staged; each file's top docstring states its stage number, inputs, and outputs. Broad shape:

- **A (`ML/emerging_symptoms/`)** — A1 anomalous encounters → A2 temporal patterns (`emerging_symptom_patterns.py`) → A3 privacy-preserving cross-hospital patterns (`cross_hospital_patterns.py`) → A4 emerging-disease inference → A5 clinical-evidence integration → A6 advanced novelty (PCA/KMeans/KDE) → A7 signal fusion (`emerging_signal_fusion.py`) → A8/A9 continuous baseline + controlled validation (`continuous_baseline.py`, `update_baseline.py`, `a9_controlled_validation.py`, `run_a9_*`). Baseline state persisted in `baseline_state.json` / `baseline_versions/`.
- **B (`ML/outbreak_detection_parent/outbreak_detection_child/`)** — B1–B7 surveillance primitives (`disease_surveillance.py`, `symptom_surveillance.py`, `historical_baseline.py`, `temporal_acceleration.py`, `persistence_detection.py`, `spatial_propagation.py`, `severity_burden.py`), B8 Objective-A integration (`objective_a_integration.py`), B9 anomaly (`anomaly_detection.py`), B10 composite risk (`outbreak_risk_engine.py` / `outbreak_risk_scoring.py`), B11 alert engine (`alert_engine.py`, GREEN/YELLOW/ORANGE/RED), B12 explainability (`explainability_engine.py`), B13 continuous-update orchestration (`continuous_update_pipeline.py`, `b13_controlled_update_test.py`), B14 controlled validation (`b14_controlled_validation.py`). `outbreak_detection.py` is the current entry; `outbreak_detection_legacy.py` is the pre-restructure version. `ML/outbreak_detection/` still exists but holds only an empty `__init__.py`.
- **E (`ML/treatment_advisor/`)** — E1 patient context → E2 candidate treatments → E3 clinical eligibility → E4 configuration (guideline / resource / availability CSVs in `e4_data/`) → E5 regional epidemiology → E6 treatment-success model (`treatment_model.py`, `treatment_success_model.pkl`) → E7 probability calibration → E8 uncertainty → E9 risk/complication → E10 recovery estimation → E11 SHAP explainability → E12 final ranking (`treatment_ranking.py`). `treatment_advisor.py` / `treatment_recommender.py` are the higher-level orchestrators.
- **Privacy (`ML/privacy/`)** — `data_minimization.py` / `data_minimization_enforcer.py`, `local_data_isolation.py`, `privacy_audit.py`, `privacy_verification.py`, `privacy_protection.py`, with `test_*.py` verification scripts.

**Note on `ML_handoff.md`:** it states the ML layer was "frozen for Review 2" and lists differential privacy, calibration, SHAP, uncertainty, etc. as future work not to present as done. The `26f6e26` "Half implementation" commit added exactly those (`probability_calibration.py`, `uncertainty_estimation.py`, `shap_explainability.py`, continuous-baseline/alert/explainability engines). Treat the handoff's "frozen" scope and honest-metrics guidance (validated FL run: Accuracy 87.82%, Micro-F1 39.23%, Macro-F1 5.83%, Hamming 12.18% — Macro-F1 low, Micro-F1 not monotonic) as still binding for reporting, but expect the code to be ahead of that doc.

## Ground rules from `ML/ML_handoff.md`

- Report FL metrics **honestly** (numbers above).
- Frontend must never touch PostgreSQL or Python ML modules directly — everything goes through a backend API.
- Use `patient_token` / pseudonyms in any application-facing view; never surface raw `patient_id`.
- Surveillance outputs stay aggregated (hospital-level, cross-hospital, pattern-level), never individual patient rows. Alert levels: GREEN / YELLOW / ORANGE / RED.
- The treatment advisor is decision support, not autonomous prescription.
