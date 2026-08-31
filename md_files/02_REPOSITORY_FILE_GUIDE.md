# Healthcare Project — Repository File Guide

## Root-level files

| File | Purpose |
|---|---|
| `database.py` | Database connection/configuration layer. |
| `database_writer.py` | Writes generated clinical data to the database. |
| `loader.py` | Loads/handles database and dataset information. |
| `main.py` | Main entry point/orchestration for the synthetic-data system. |
| `prepare_ml_data.py` | Prepares hospital-level datasets for ML. |
| `run_multihospital_simulation.py` | Runs the multi-hospital simulation workflow. |
| `inspect_schema.py` | Inspects database schema. |
| `inspect_all_schemas.py` | Inspects database schemas. |
| `list_tables.py` | Lists database tables. |
| `test_*.py` | Tests for generation, database and pipeline functionality. |

## `generators/`

Synthetic clinical-data generators:
- `demographics_generator.py` — demographics
- `disease_generator.py` — diseases
- `symptom_generator.py` — symptoms
- `symptom_onset_generator.py` — symptom onset
- `vitals_generator.py` — vital signs
- `severity_generator.py` — severity
- `treatment_generator.py` — treatments
- `complication_generator.py` — complications
- `outcome_generator.py` — clinical outcomes
- `encounter_generator.py` — encounters
- `daily_hospital_generator.py` — hospital/day generation

## `datasets/`

### `datasets/config/`
- `disease_generation_config.csv`
- `hospital_generation_config.csv`
- `vital_range_config.csv`

These configure synthetic data generation.

### `datasets/knowledge tables/`
- `hospital_master.csv`
- `disease_master.csv`
- `symptom_master.csv`
- `treatment_master.csv`
- `severity_master.csv`
- `complication_master.csv`
- `disease_symptom_mapping.csv`
- `disease_treatment_mapping.csv`
- `disease_complication_mapping.csv`

`import_tables.py` imports knowledge-table data into PostgreSQL. Its CSV path is project-relative.

## `models/`

Database model definitions:
- `encounter.py`
- `daily_hospital.py`
- `test_encounter.py`

## `services/`

Database/application helpers:
- `lookup_service.py`
- `postgres_loader.py`

## `ML/`

### `ML/emerging_symptoms/`
- `emerging_symptom_model.py` — atypical/emerging symptom modelling
- `emerging_symptom_patterns.py` — recurring/anomalous combinations
- `cross_hospital_patterns.py` — cross-hospital symptom aggregation

Supports Objective A.

### `ML/outbreak_detection/`
- `outbreak_detection.py` — weekly cases, growth, alerts and outbreak assessment

Supports Objective B.

### `ML/federated_learning/`
- `flower_client.py` — hospital-side local training/evaluation
- `flower_server.py` — Flower server and FedAvg
- `model_utils.py` — shared TabNet/model utilities
- `task.py` — FL task/data configuration

Supports Objective C.

### `ML/privacy/`
- `privacy_audit.py` — field privacy classification
- `data_minimization.py` — field-use/minimization rules
- `privacy_protection.py` — pseudonymization
- `privacy_verification.py` — privacy verification checks
- `privacy_enforcement_audit.py` — additional audit validation

### `ML/local_models/`
- `local_symptom_model.py` — local symptom model implementation

### `ML/treatment_advisor/`
- `treatment_model.py` — Random Forest treatment-success model
- `candidate_treatments.py` — valid treatment candidates
- `treatment_recommender.py` — treatment ranking
- `recovery_estimator.py` — historical recovery estimate
- `risk_information.py` — complication/risk information
- `treatment_advisor.py` — combines advisor components

Supports Objective E.

### `ML/data/`
Generated outputs:
- `privacy_audit.csv`
- `data_minimization_matrix.csv`
- `hospital_symptom_pattern_counts.csv`
- `cross_hospital_symptom_patterns.csv`
- `weekly_hospital_cases.csv`
- `outbreak_surveillance.csv`

### `ML/models/`
- `treatment_success_model.pkl` — trained treatment-success model

### Hospital ML datasets

`ml_data_H001.csv` through `ml_data_H010.csv` represent the ten simulated hospital-local analytical datasets used in the FL demonstration.

## Security/configuration

`.env` and local `config.py` are intentionally excluded from GitHub. Each developer should configure their own local environment and never commit secrets.
