# Healthcare Project — Backend and Frontend Integration Guide

## Goal

Integrate the existing ML and database implementation into a clean Review 2 prototype. Do not redesign or replace the existing ML algorithms.

## Architecture

```text
Frontend
    |
    | HTTP/JSON
    v
Backend API
    |
    +----> PostgreSQL
    |
    +----> ML modules
    |
    +----> Generated ML artifacts
```

The frontend must not connect directly to PostgreSQL, raw datasets or Python ML files.

## Six core views

1. Dashboard
2. Clinical / Patient
3. Surveillance
4. Federated Learning
5. Treatment Advisor
6. Privacy / Audit

## Dashboard

Show:
- 10 hospitals monitored
- overall outbreak status
- hospitals with RED alerts
- affected-hospital percentage
- latest FL round/status
- global FL metrics
- privacy status
- recent symptom-pattern summary

## Clinical / Patient

Show:
- patient token/pseudonym
- age
- gender
- symptoms
- temperature
- heart rate
- respiratory rate
- systolic/diastolic BP
- SpO2
- disease
- severity
- admission/visit/discharge information where appropriate
- relevant onset/travel/vaccination information if available

Do not expose raw patient IDs in analytical/application views.

## Surveillance

Show:
- hospital ID
- current cases
- previous cases
- growth rate
- alert level
- overall alert level
- potential outbreak signal
- affected-hospital percentage
- emerging/recurring symptom patterns
- cross-hospital patterns

Charts can show case growth and alert distribution.

## Federated Learning

Show:
- 10 simulated hospitals
- H001–H010 participation
- 3 completed rounds
- FedAvg
- global metrics

Validated final metrics:
- Accuracy: 87.82%
- Micro-F1: 39.23%
- Macro-F1: 5.83%
- Hamming Loss: 12.18%

Recommended visual:

```text
Local Data
    |
    v
Local Training
    |
    v
Model Update
    |
    v
FedAvg
    |
    v
Global Model
```

Prominently state:

> Raw patient data remains at hospital level.

Do not claim differential privacy or secure aggregation as implemented unless separately validated.

Do not start a full FL simulation every time the dashboard opens. Display the latest completed run/status.

## Treatment Advisor

Input:
- age
- gender where relevant
- symptoms
- vital signs
- disease
- severity

Output:
- ranked treatment options
- predicted success probability
- priority/first-line/referral metadata
- expected historical recovery days
- potential complications/risks

The advisor is clinical decision support, not autonomous prescription.

Validated example:
- Disease D004
- Severity SV001
- T001: 74.02%
- T006: 71.54%
- Expected historical recovery: 5.01 days

## Privacy / Audit

Show:
- 46 audited columns
- privacy classification
- data-minimization matrix
- pseudonym generation: PASS
- pseudonym uniqueness: PASS
- original identifier removal: PASS
- deterministic local linkage: PASS

## Recommended API targets

These are integration targets for the backend:

```text
GET  /api/dashboard
GET  /api/surveillance
GET  /api/federated-learning/status
POST /api/treatment/recommend
GET  /api/privacy/status
GET  /api/hospitals
GET  /api/encounters/{token}
POST /api/encounters
```

These endpoint names are recommendations for integration, not claims that all of them already exist.

## Integration rules

- Frontend consumes backend JSON only.
- Frontend does not connect directly to PostgreSQL.
- Frontend does not import Python ML files.
- Raw `patient_id` must not appear in analytical dashboards.
- Use pseudonymous patient tokens where needed.
- Surveillance should remain aggregated at hospital/pattern level.
- FL should exchange model information rather than raw patient rows.
- Treatment output must be labelled as clinical decision support.
- Do not invent new ML features for Review 2.

## Recommended Review 2 demo

1. Dashboard
2. Pseudonymized clinical encounter
3. Treatment Advisor
4. Surveillance/outbreak status
5. Federated Learning with 10 hospitals and metrics
6. Privacy/Audit PASS
7. Explain local patient-data protection and collaborative model/aggregate use
