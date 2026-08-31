Healthcare Project — ML Handoff
1. Purpose

This document describes the ML components currently implemented for the Healthcare Project and provides the backend/frontend team with the information required to integrate them into the application.

The ML layer currently supports the project's five implementation areas:

Objective A — Atypical Symptom Detection
Objective B — Outbreak Detection and Surveillance
Objective C — Federated Learning
Objective D — Structured Local Clinical Database
Objective E — AI Treatment Advisor

The backend should provide the controlled interface between the ML/database layer and the frontend. The frontend should not directly access PostgreSQL or Python ML modules.

2. Current ML Structure
ML/
│
├── federated_learning/
│   ├── __init__.py
│   ├── flower_client.py
│   ├── flower_server.py
│   ├── model_utils.py
│   └── task.py
│
├── emerging_symptoms/
│   ├── __init__.py
│   ├── emerging_symptom_model.py
│   ├── emerging_symptom_patterns.py
│   └── cross_hospital_patterns.py
│
├── outbreak_detection/
│   ├── __init__.py
│   └── outbreak_detection.py
│
├── treatment_advisor/
│   ├── __init__.py
│   ├── candidate_treatments.py
│   ├── recovery_estimator.py
│   ├── risk_information.py
│   ├── treatment_advisor.py
│   ├── treatment_model.py
│   └── treatment_recommender.py
│
├── privacy/
│   ├── __init__.py
│   ├── data_minimization.py
│   ├── privacy_audit.py
│   ├── privacy_enforcement_audit.py
│   ├── privacy_protection.py
│   └── privacy_verification.py
│
├── local_models/
│   ├── __init__.py
│   └── local_symptom_model.py
│
├── data/
│   ├── cross_hospital_symptom_patterns.csv
│   ├── hospital_symptom_pattern_counts.csv
│   ├── weekly_hospital_cases.csv
│   ├── outbreak_surveillance.csv
│   ├── privacy_audit.csv
│   └── data_minimization_matrix.csv
│
├── models/
│   └── treatment_success_model.pkl
│
└── pyproject.toml
3. Objective A — Atypical Symptom Detection
Purpose

Identify recurring, unusual or emerging symptom patterns that may indicate atypical disease behaviour.

Files
emerging_symptoms/emerging_symptom_model.py
emerging_symptoms/emerging_symptom_patterns.py
emerging_symptoms/cross_hospital_patterns.py
Responsibilities

emerging_symptom_model.py

Performs symptom-pattern modelling.
Provides the underlying modelling functionality for identifying unusual/emerging patterns.

emerging_symptom_patterns.py

Detects recurring/anomalous symptom combinations.

cross_hospital_patterns.py

Aggregates symptom patterns across hospitals.
Outputs
data/cross_hospital_symptom_patterns.csv
data/hospital_symptom_pattern_counts.csv

These outputs can be used by the backend for the Surveillance page.

4. Objective B — Outbreak Detection and Surveillance
Purpose

Detect increases in hospital-level cases and generate outbreak alerts.

File
outbreak_detection/outbreak_detection.py
Outputs
data/weekly_hospital_cases.csv
data/outbreak_surveillance.csv

The surveillance output contains hospital-level information such as:

current cases
previous cases
growth
alert level
outbreak assessment

Alert levels:

GREEN
YELLOW
ORANGE
RED

The backend should expose these as aggregated surveillance information rather than exposing individual patient records.

5. Objective C — Federated Learning
Purpose

Enable multiple hospitals to collaboratively train a multi-label symptom model without sending their raw patient records to a central server.

The current prototype uses:

10 simulated hospitals
TabNet
FedAvg
3 training rounds
27 symptom labels
Files
federated_learning/task.py

Handles:

feature preparation
hospital dataset loading
multi-label target configuration
federated_learning/model_utils.py

Handles:

TabNet model creation
model parameters
training utilities
federated_learning/flower_client.py

Represents the hospital-side FL client.

The client:

loads local data
      ↓
trains locally
      ↓
evaluates locally
      ↓
returns model information
federated_learning/flower_server.py

Coordinates the federated-learning process and FedAvg aggregation.

Hospital datasets
ml_data_H001.csv
ml_data_H002.csv
...
ml_data_H010.csv

These represent the ten simulated hospital datasets used by the FL demonstration.

Validated result

The final successful FL validation used:

Hospitals: 10
Rounds: 3
Model: TabNet
Aggregation: FedAvg
Task: Multi-label symptom prediction

Final global metrics:

Accuracy:       87.82%
Micro-F1:       39.23%
Macro-F1:        5.83%
Hamming Loss:   12.18%

The results should be displayed honestly. Accuracy and Hamming loss improved, but Micro-F1 did not improve monotonically and Macro-F1 remained relatively low.

Privacy boundary

The current simulation keeps raw patient records on the simulated hospital side. The federated server receives model information rather than raw patient rows.

The frontend should display this boundary explicitly.

6. Objective D — Structured Local Clinical Database

The database component provides the structured clinical-data foundation used by the ML and surveillance workflows.

Main database layer
database.py
database_writer.py
loader.py
Clinical data

The database contains structures for:

patient encounters
encounter symptoms
encounter treatments
encounter complications

as well as master/mapping information for:

diseases
symptoms
treatments
severity
complications
hospitals

The database supports:

surveillance
federated-learning data preparation
treatment recommendation
structured clinical-data workflows

The backend should expose database functionality through APIs rather than allowing the frontend to connect directly to PostgreSQL.

7. Objective E — AI Treatment Advisor
Purpose

Provide ranked treatment decision support using patient clinical information and historical treatment outcomes.

Files
treatment_advisor/candidate_treatments.py
treatment_advisor/treatment_model.py
treatment_advisor/treatment_recommender.py
treatment_advisor/recovery_estimator.py
treatment_advisor/risk_information.py
treatment_advisor/treatment_advisor.py
Workflow
Patient clinical information
          ↓
Disease + severity
          ↓
Candidate treatments
          ↓
Treatment-success prediction
          ↓
Treatment ranking
          ↓
Recovery estimation
          ↓
Risk information
          ↓
Final treatment decision support
Treatment model

The treatment-success model is a:

Random Forest Classifier

It was trained on:

14,165 treatment records

using an encounter-level leakage-aware split with zero encounter overlap.

Validation:

Accuracy: 0.8799
ROC-AUC:  0.6317

The trained model is stored at:

models/treatment_success_model.pkl
Advisor output

The backend can expose:

ranked treatment options
predicted success probability
treatment priority metadata
expected historical recovery time
potential complications/risks

The treatment advisor is clinical decision support, not an autonomous prescription system.

8. Privacy Components

Although privacy is Objective D's privacy/security aspect within the overall project architecture, the privacy-specific ML utilities are maintained separately because they support the protection and verification requirements across the system.

Files
privacy/privacy_audit.py
privacy/data_minimization.py
privacy/privacy_protection.py
privacy/privacy_verification.py
privacy/privacy_enforcement_audit.py
Current validation

The privacy workflow has demonstrated:

Pseudonym generation:                    PASS
Pseudonym uniqueness:                   PASS
Original identifier removed:            PASS
Deterministic local linkage:            PASS

The privacy audit covers 46 database columns and classifies them according to privacy relevance.

Generated artifacts:

data/privacy_audit.csv
data/data_minimization_matrix.csv

The backend/frontend should use pseudonymous patient tokens rather than exposing raw patient identifiers in application views.

9. What the Backend Should Provide

The recommended backend interfaces are:

GET  /api/dashboard

GET  /api/surveillance

GET  /api/federated-learning/status

POST /api/treatment/recommend

GET  /api/privacy/status

GET  /api/hospitals

GET  /api/encounters/{token}

POST /api/encounters

These endpoints are integration targets; the backend team should implement them around the existing ML/database functionality rather than creating new ML algorithms. The existing display specification also identifies these six application areas: Dashboard, Clinical/Patient, Surveillance, Federated Learning, Treatment Advisor, and Privacy/Audit.

10. What the Frontend Should Display
Dashboard

Display:

hospitals monitored
overall outbreak status
affected hospitals
latest FL status
global ML metrics
privacy status
recent symptom patterns
Clinical / Patient

Display:

patient pseudonym/token
age
gender where appropriate
symptoms
vital signs
disease
severity
encounter information

Do not display the raw patient identifier in analytical views.

Surveillance

Display:

hospital ID
cases
previous cases
growth rate
alert level
overall outbreak status
emerging symptom patterns
cross-hospital patterns
Federated Learning

Display:

10 hospitals
3 rounds
FedAvg
H001–H010 participation
global metrics
local-data boundary

Recommended visual:

Local Data
    ↓
Local Training
    ↓
Model Update
    ↓
FedAvg
    ↓
Global Model

Prominently state:

Raw patient data remains at hospital level.

Treatment Advisor

Provide clinical input fields and display:

ranked treatments
success probability
priority metadata
expected recovery days
risks/complications
decision-support disclaimer
Privacy / Audit

Display:

privacy classification
data-minimization summary
pseudonymization status
verification results
PASS/FAIL status
11. Integration Rules
Rule 1 — Frontend does not access ML directly

Use:

Frontend
   ↓
Backend API
   ↓
ML / Database

Not:

Frontend
   ↓
Python ML files
Rule 2 — Frontend does not access PostgreSQL directly

All database access should go through the backend.

Rule 3 — Don't expose raw patient IDs

Use:

patient_token

where an application identifier is necessary.

Rule 4 — Keep surveillance aggregated

Surveillance pages should primarily expose:

hospital-level
cross-hospital
pattern-level

information.

Rule 5 — Don't start FL every time the dashboard opens

The dashboard should display the latest completed FL status/results.

Rule 6 — Don't invent new ML functionality

The current Review 2 goal is integration of the existing implementation.

12. Current ML Completion Status
Component	Status
Atypical symptom modelling	✅ Implemented
Emerging/recurring symptom patterns	✅ Implemented
Cross-hospital symptom analysis	✅ Implemented
Outbreak detection	✅ Implemented
Hospital alert levels	✅ Implemented
Federated learning	✅ Implemented
10-hospital simulation	✅ Validated
Multi-label TabNet model	✅ Validated
Privacy audit	✅ Implemented
Data minimization	✅ Implemented
Pseudonymization	✅ Validated
Privacy verification	✅ Validated
Structured clinical database	✅ Foundation implemented
Treatment-success model	✅ Validated
Treatment recommendation	✅ Implemented

The project status report records the core prototype as substantially implemented, with the remaining Review 2 work focused primarily on backend/frontend integration, end-to-end privacy validation, final system testing and demonstration preparation.

13. What Remains for the Team
ML

Status: essentially frozen for Review 2.

No major new ML functionality should be added now.

Backend

Remaining:

API integration
database service integration
ML service integration
controlled data access
application-level privacy enforcement
Frontend

Remaining:

Dashboard
Clinical/Patient view
Surveillance
Federated Learning
Treatment Advisor
Privacy/Audit
Joint

Remaining:

end-to-end privacy audit
complete application workflow
integration testing
final Review 2 demonstration
14. Future Work — Do Not Present as Completed

The original project architecture describes additional advanced capabilities such as:

differential privacy
secure multiparty aggregation
FedProx/FedNova
gradient compression/quantization
transformer/GNN/time-series models
SHAP/attention explainability
production encryption/RBAC
HMIS integration
Docker deployment
asynchronous participation
model versioning/rollback
offline inference

These should be described as future extensions, not current Review 2 functionality.

15. ML Handoff Checklist
[✓] ML source code organized
[✓] Dependencies configured
[✓] Hospital datasets available
[✓] Federated learning validated
[✓] Treatment model available
[✓] Privacy components validated
[✓] Surveillance components validated
[✓] Generated artifacts organized
[✓] Backend integration requirements defined
[✓] Frontend display requirements defined

[ ] Backend API integration
[ ] Frontend integration
[ ] End-to-end privacy audit
[ ] Complete application workflow
[ ] Final system testing
[ ] Review 2 demonstration