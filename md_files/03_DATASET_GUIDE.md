# Healthcare Project — Dataset and Data Guide

## Data source

The current Review 2 prototype uses synthetic healthcare data. It represents hospital encounters and related clinical information without relying on real patient records.

## Knowledge tables

Location:

```text
datasets/knowledge tables/
```

Reference tables:
- `hospital_master.csv` — hospital/facility references
- `disease_master.csv` — diseases
- `symptom_master.csv` — symptoms
- `treatment_master.csv` — treatments
- `severity_master.csv` — severity categories
- `complication_master.csv` — complications

Mapping tables:
- `disease_symptom_mapping.csv` — disease/symptom relationships
- `disease_treatment_mapping.csv` — disease/severity/treatment relationships
- `disease_complication_mapping.csv` — disease/complication relationships

## Generation configuration

Location:

```text
datasets/config/
```

Files:
- `disease_generation_config.csv`
- `hospital_generation_config.csv`
- `vital_range_config.csv`

## Hospital-local ML datasets

```text
ml_data_H001.csv
ml_data_H002.csv
...
ml_data_H010.csv
```

These represent ten simulated hospitals and are especially important for federated learning.

Conceptually:

```text
H001 local data --> local training
H002 local data --> local training
...
H010 local data --> local training
          |
          v
   local model updates
          |
          v
        FedAvg
          |
          v
     global model
```

Raw patient-level rows are not sent to the FL server in the current workflow.

## ML generated outputs

- `ML/data/privacy_audit.csv` — 46-column privacy classification
- `ML/data/data_minimization_matrix.csv` — field-use/minimization rules
- `ML/data/hospital_symptom_pattern_counts.csv` — hospital-level symptom counts
- `ML/data/cross_hospital_symptom_patterns.csv` — cross-hospital symptom aggregation
- `ML/data/weekly_hospital_cases.csv` — weekly cases and growth
- `ML/data/outbreak_surveillance.csv` — outbreak/alert assessment

## Model artifact

```text
ML/models/treatment_success_model.pkl
```

Random Forest treatment-success model.

Validation:
- 14,165 treatment records
- encounter-level leakage-aware split
- zero encounter overlap
- Accuracy: 0.8799
- ROC-AUC: 0.6317

## Database

Important clinical tables include:
- `patient_encounter`
- `encounter_symptoms`
- `encounter_treatments`
- `encounter_complications`

Reference/master data covers hospitals, diseases, symptoms, treatments, severity and complications.

## Privacy handling

The application should use pseudonymous patient tokens where an application identifier is required.

Current privacy verification checks:
- pseudonym generation
- pseudonym uniqueness
- original identifier removal from analytical view
- deterministic local linkage

All four checks have passed in the current prototype.

## Important rule

Frontend must not connect directly to PostgreSQL or raw datasets.

Use:

```text
Frontend
   |
   v
Backend API
   |
   v
Database / ML
```
