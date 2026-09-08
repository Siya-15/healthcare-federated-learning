"""Static seed content for the Supabase application schema.

The dashboard_snapshot payloads mirror the frontend fixtures
(frontend/src/mocks/*.js) 1:1 so the live API returns the same shapes the UI
already renders. Honest FL metrics and NOT_IMPLEMENTED markers are preserved
(spec section 16).
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# Reference / master data
# --------------------------------------------------------------------------
HOSPITALS = [
    (f"H{str(i + 1).zfill(3)}", f"Hospital H{str(i + 1).zfill(3)}", "District " + chr(65 + i), "State")
    for i in range(10)
]

DISEASES = [
    ("D001", "Influenza"),
    ("D002", "COVID-19"),
    ("D003", "Dengue"),
    ("D004", "Typhoid"),
    ("D005", "Malaria"),
    ("D006", "Tuberculosis"),
    ("D007", "Pneumonia"),
    ("D008", "Acute Bronchitis"),
    ("D404", "Unmapped Presentation"),
]

SEVERITIES = [
    ("SV001", "Mild"),
    ("SV002", "Moderate"),
    ("SV003", "Severe"),
]

SYMPTOMS = [
    "Abdominal Pain", "Anaemia", "Bleeding", "Breathlessness", "Chest Pain", "Chills",
    "Dehydration", "Diarrhoea", "Dry Cough", "Fatigue", "Fever", "Headache", "Joint Pain",
    "Loss of Appetite", "Loss of Smell", "Loss of Taste", "Muscle Pain", "Nausea",
    "Night Sweats", "Persistent Cough", "Rash", "Retro-orbital Pain", "Runny Nose",
    "Sore Throat", "Sweating", "Vomiting", "Weight Loss",
]

TREATMENTS = [
    ("T001", "Oseltamivir + supportive care", "Antiviral for influenza-like illness"),
    ("T002", "IV fluid resuscitation + supportive care", "Volume support for febrile dehydrating illness"),
    ("T003", "Antipyretics + rest + oral fluids", "Symptomatic outpatient management"),
    ("T004", "Oxygen therapy + inpatient monitoring", "Respiratory support for hypoxia"),
    ("T005", "Oral rehydration + outpatient monitoring", "Low-resource supportive pathway"),
    ("T006", "Ceftriaxone course", "Empirical antibiotic for enteric fever"),
    ("T007", "Artemisinin-based combination therapy", "First-line antimalarial"),
    ("T008", "Standard anti-TB regimen (HRZE)", "Directly observed TB therapy"),
    ("T009", "High-dose NSAID protocol", "Anti-inflammatory analgesia"),
    ("T010", "Bronchodilator + short steroid course", "Airways management for bronchitis"),
    ("T011", "Platelet transfusion protocol", "Reserved for bleeding / critical thrombocytopenia"),
    ("T012", "Broad respiratory antibiotics + admission", "Community-acquired pneumonia inpatient"),
    ("T013", "Amoxicillin outpatient course", "Mild bacterial respiratory infection"),
    ("T014", "Broad-spectrum antibiotics", "Empirical coverage pending workup"),
]

# disease_id, severity_id (None = any), treatment_id, is_first_line, line_rank
DISEASE_TREATMENT_MAPPING = [
    ("D001", None, "T001", True, 1),
    ("D001", None, "T003", False, 2),
    ("D001", None, "T014", False, 5),
    ("D002", None, "T004", True, 1),
    ("D002", None, "T003", False, 2),
    ("D002", None, "T014", False, 5),
    ("D003", None, "T002", True, 1),
    ("D003", None, "T005", False, 2),
    ("D003", None, "T011", False, 4),
    ("D003", None, "T014", False, 5),
    ("D003", None, "T009", False, 6),
    ("D004", None, "T006", True, 1),
    ("D004", None, "T003", False, 3),
    ("D005", None, "T007", True, 1),
    ("D005", None, "T002", False, 3),
    ("D006", None, "T008", True, 1),
    ("D007", None, "T012", True, 1),
    ("D007", None, "T004", False, 2),
    ("D007", None, "T013", False, 3),
    ("D008", None, "T010", True, 1),
    ("D008", None, "T003", False, 2),
    ("D404", None, "T009", False, 5),
]

# treatment_id, disease_id (None = global), stage, reason
TREATMENT_CONTRAINDICATION = [
    (
        "T009",
        "D003",
        "E3",
        "E3 clinical eligibility: NSAIDs contraindicated in suspected dengue (bleeding risk). Removed before ranking.",
    ),
    (
        "T009",
        "D404",
        "E3",
        "E3 clinical eligibility: high-dose NSAID protocol not eligible for this presentation.",
    ),
]

# per-treatment posture applied to every hospital (availability, guideline, tier)
TREATMENT_CONFIG_DEFAULTS = {
    "T001": ("AVAILABLE", "PROJECT_SUPPORTED", "LOW"),
    "T002": ("AVAILABLE", "PROJECT_SUPPORTED", "LOW"),
    "T003": ("AVAILABLE", "PROJECT_SUPPORTED", "LOW"),
    "T004": ("AVAILABLE", "PROJECT_SUPPORTED", "MEDIUM"),
    "T005": ("AVAILABLE", "PROJECT_SUPPORTED_REVIEW", "LOW"),
    "T006": ("AVAILABLE", "PROJECT_SUPPORTED", "MEDIUM"),
    "T007": ("AVAILABLE", "PROJECT_SUPPORTED", "MEDIUM"),
    "T008": ("AVAILABLE", "PROJECT_SUPPORTED", "MEDIUM"),
    "T009": ("AVAILABLE", "NOT_SUPPORTED", "MEDIUM"),
    "T010": ("AVAILABLE", "PROJECT_SUPPORTED", "LOW"),
    "T011": ("LIMITED", "NOT_SUPPORTED", "HIGH"),
    "T012": ("AVAILABLE", "PROJECT_SUPPORTED", "HIGH"),
    "T013": ("AVAILABLE", "PROJECT_SUPPORTED", "LOW"),
    "T014": ("AVAILABLE", "NOT_SUPPORTED", "MEDIUM"),
}

# a couple of hospital-specific overrides so E4 visibly varies by site
TREATMENT_CONFIG_OVERRIDES = [
    ("T011", "H001", "LIMITED", "NOT_SUPPORTED", "HIGH"),
    ("T004", "H007", "LIMITED", "PROJECT_SUPPORTED", "HIGH"),
    ("T012", "H009", "LIMITED", "PROJECT_SUPPORTED", "HIGH"),
]

# --------------------------------------------------------------------------
# Canonical sample encounters (keep tokens the UI already references)
# --------------------------------------------------------------------------
CANONICAL_ENCOUNTERS = [
    {
        "encounter_id": "ENC-7B7DEBF90A", "patient_token": "pt_9f4c1a2b", "hospital_id": "H001",
        "visit_timestamp": "2026-09-08T08:30:00Z", "age": 54, "gender": "Female",
        "disease_id": "D003", "severity_id": "SV002",
        "symptoms": ["Fever", "Headache", "Joint Pain", "Rash", "Retro-orbital Pain"],
        "discharge_status": "Stable", "temperature": 38.9, "heart_rate": 104,
        "respiratory_rate": 20, "spo2": 96, "systolic_bp": 108, "diastolic_bp": 72,
    },
    {
        "encounter_id": "ENC-4C1A9930F2", "patient_token": "pt_2a7710de", "hospital_id": "H001",
        "visit_timestamp": "2026-09-07T14:05:00Z", "age": 33, "gender": "Male",
        "disease_id": "D001", "severity_id": "SV001",
        "symptoms": ["Fever", "Muscle Pain", "Fatigue", "Sore Throat"],
        "discharge_status": "Recovered", "temperature": 37.8, "heart_rate": 88,
        "respiratory_rate": 16, "spo2": 98, "systolic_bp": 120, "diastolic_bp": 78,
    },
    {
        "encounter_id": "ENC-9920AB77C1", "patient_token": "pt_bb31c0a4", "hospital_id": "H001",
        "visit_timestamp": "2026-09-06T10:45:00Z", "age": 68, "gender": "Male",
        "disease_id": "D007", "severity_id": "SV003",
        "symptoms": ["Breathlessness", "Chest Pain", "Persistent Cough", "Fatigue", "Chills"],
        "discharge_status": "Referred", "temperature": 38.2, "heart_rate": 112,
        "respiratory_rate": 26, "spo2": 90, "systolic_bp": 104, "diastolic_bp": 68,
    },
    {
        "encounter_id": "ENC-1D5E4402B8", "patient_token": "pt_57e9f130", "hospital_id": "H002",
        "visit_timestamp": "2026-09-06T09:10:00Z", "age": 41, "gender": "Female",
        "disease_id": "D002", "severity_id": "SV002",
        "symptoms": ["Dry Cough", "Loss of Smell", "Loss of Taste", "Fatigue", "Headache"],
        "discharge_status": "Stable", "temperature": 38.0, "heart_rate": 96,
        "respiratory_rate": 18, "spo2": 95, "systolic_bp": 118, "diastolic_bp": 76,
    },
    {
        "encounter_id": "ENC-NOCAND01", "patient_token": "pt_nocand01", "hospital_id": "H001",
        "visit_timestamp": "2026-09-05T11:00:00Z", "age": 47, "gender": "Male",
        "disease_id": "D404", "severity_id": "SV002",
        "symptoms": ["Fatigue", "Headache"],
        "discharge_status": "Stable", "temperature": 37.5, "heart_rate": 84,
        "respiratory_rate": 16, "spo2": 98, "systolic_bp": 122, "diastolic_bp": 80,
    },
]

# --------------------------------------------------------------------------
# dashboard_snapshot payloads (kind -> JSON)  -- mirror of frontend/src/mocks
# --------------------------------------------------------------------------
_WEEKS = ["2026-W28", "2026-W29", "2026-W30", "2026-W31", "2026-W32", "2026-W33"]

SNAPSHOTS: dict[str, dict] = {
    "doctor.dashboard": {
        "hospital_id": "H001",
        "ward": "Ward 4B — Cardiology",
        "recent_encounters": 3,
        "encounters_today": 1,
        "local_alert": {
            "disease_name": "Dengue", "alert_level": "ORANGE", "hospital_id": "H004",
            "note": "Regional signal near your network.",
        },
        "model_status": {
            "advisor": "READY", "global_model_version": "fl-global-r3", "last_fl_run": "2026-09-06",
        },
        "kpis": {
            "active_patients": {"value": 1284, "delta": "3.2% vs last week", "deltaTone": "up",
                                "spark": [980, 1010, 1005, 1060, 1120, 1180, 1240, 1284]},
            "critical_alerts": {"value": 7, "delta": "2 new since 6am", "deltaTone": "warn",
                                "spark": [3, 4, 2, 5, 4, 6, 5, 7]},
            "avg_recovery_score": {"value": 84.6, "delta": "1.8 pts this month", "deltaTone": "warn",
                                   "spark": [82.1, 82.4, 83.0, 82.8, 83.6, 84.0, 84.2, 84.6]},
            "advisor_runs": {"value": 42, "delta": "9 today", "deltaTone": "up",
                             "spark": [18, 22, 20, 27, 25, 31, 36, 42]},
        },
        "weekly_admissions": [
            {"x": "Mon", "Emergency": 41, "Scheduled": 32},
            {"x": "Tue", "Emergency": 49, "Scheduled": 37},
            {"x": "Wed", "Emergency": 37, "Scheduled": 27},
            {"x": "Thu", "Emergency": 52, "Scheduled": 38},
            {"x": "Fri", "Emergency": 46, "Scheduled": 35},
        ],
        "diagnosis_mix": [
            {"name": "Influenza", "value": 322}, {"name": "COVID-19", "value": 268},
            {"name": "Dengue", "value": 214}, {"name": "Pneumonia", "value": 176},
            {"name": "Typhoid", "value": 141}, {"name": "Malaria", "value": 98},
            {"name": "Other", "value": 65},
        ],
        "priority_queue": [
            {"patient_token": "pt_bb31c0a4", "risk": "HIGH", "reason": "Rising resp. rate + low SpO₂", "disease_name": "Pneumonia"},
            {"patient_token": "pt_9f4c1a2b", "risk": "MODERATE", "reason": "Platelet trend + dengue day 4", "disease_name": "Dengue"},
            {"patient_token": "pt_57e9f130", "risk": "MODERATE", "reason": "Persistent hypoxia on room air", "disease_name": "COVID-19"},
        ],
    },
    "surveillance.overview": {
        "monitored_hospitals": 10,
        "current_alert_level": "ORANGE",
        "active_signals": 4,
        "surveillance_period": f"{_WEEKS[0]} → {_WEEKS[-1]}",
        "updated_at": "2026-09-07",
        "scope_note": "Weekly hospital-level surveillance and anomalous symptom-pattern detection (audited prototype). Not clinically validated pathogen or outbreak confirmation.",
        "headline_signals": [
            {"hospital_id": "H004", "disease_name": "Dengue", "alert_level": "ORANGE", "driver": "Case growth + symptom-cluster persistence"},
            {"hospital_id": "H007", "disease_name": "Influenza", "alert_level": "YELLOW", "driver": "Above-baseline weekly count"},
            {"hospital_id": "H002", "disease_name": "COVID-19", "alert_level": "YELLOW", "driver": "Rising respiratory-symptom cluster"},
            {"hospital_id": "H009", "disease_name": "Typhoid", "alert_level": "GREEN", "driver": "Within expected range"},
        ],
    },
    "surveillance.alerts": {
        "items": [
            {"id": "ALRT-0041", "hospital_id": "H004", "disease_name": "Dengue", "alert_level": "ORANGE",
             "score": 0.71, "week": "2026-W33",
             "drivers": ["Weekly count 2.4x baseline", "Symptom cluster persisted 3 weeks", "Cross-hospital corroboration (H003)"],
             "recommended_action": "Escalated surveillance; verify vector-control status; review admissions capacity.",
             "persistence_weeks": 3, "spatial_note": "Signal also present at a neighbouring hospital (H003)."},
            {"id": "ALRT-0042", "hospital_id": "H007", "disease_name": "Influenza", "alert_level": "YELLOW",
             "score": 0.44, "week": "2026-W33",
             "drivers": ["Weekly count 1.5x baseline", "Fever + Muscle Pain + Fatigue cluster"],
             "recommended_action": "Continue monitoring; no escalation yet.",
             "persistence_weeks": 1, "spatial_note": "Isolated to H007 this week."},
            {"id": "ALRT-0043", "hospital_id": "H002", "disease_name": "COVID-19", "alert_level": "YELLOW",
             "score": 0.39, "week": "2026-W33",
             "drivers": ["Rising Breathlessness + Persistent Cough cluster", "Count near baseline but accelerating"],
             "recommended_action": "Monitor acceleration; recheck next week.",
             "persistence_weeks": 2, "spatial_note": "Isolated to H002."},
        ]
    },
    "surveillance.emerging_symptoms": {
        "scope_note": "Objective A detects unusual / recurring symptom combinations relative to a rolling baseline. It does NOT infer a new pathogen or variant.",
        "patterns": [
            {"pattern": "Fever + Rash + Retro-orbital Pain + Joint Pain", "hospital_count": 3, "frequency": 58, "emergence_score": 0.68, "status": "WATCH", "first_seen": "2026-W31"},
            {"pattern": "Breathlessness + Persistent Cough + Fatigue", "hospital_count": 2, "frequency": 41, "emergence_score": 0.52, "status": "WATCH", "first_seen": "2026-W32"},
            {"pattern": "Diarrhoea + Vomiting + Dehydration + Abdominal Pain", "hospital_count": 4, "frequency": 73, "emergence_score": 0.47, "status": "MONITOR", "first_seen": "2026-W30"},
            {"pattern": "Loss of Smell + Loss of Taste + Headache", "hospital_count": 1, "frequency": 12, "emergence_score": 0.21, "status": "MONITOR", "first_seen": "2026-W33"},
        ],
    },
    "surveillance.trends": {
        "weeks": _WEEKS,
        "series": [
            {"disease_name": "Dengue", "observed": [34, 41, 52, 63, 88, 120], "baseline": [40, 40, 42, 44, 45, 45]},
            {"disease_name": "Influenza", "observed": [61, 58, 64, 70, 77, 92], "baseline": [60, 60, 61, 62, 62, 63]},
            {"disease_name": "COVID-19", "observed": [22, 20, 25, 28, 33, 39], "baseline": [24, 24, 24, 25, 25, 25]},
        ],
        "growth_note": "Growth = observed vs rolling baseline. Prototype signal, not a forecast.",
    },
    "federated.network": {
        "framework": "Flower (flwr) — FedAvg",
        "model": "TabNet multi-label classifier (27 symptom labels)",
        "total_hospitals": 10,
        "participating_hospitals": 10,
        "current_round": 3,
        "total_rounds": 3,
        "global_model_version": "fl-global-r3",
        "last_run": "2026-09-06T18:20:00Z",
        "aggregation_status": "COMPLETE",
        "hospitals": [
            {"hospital_id": f"H{str(i + 1).zfill(3)}", "local_training": "COMPLETE",
             "update_submitted": True, "update_approved": True, "local_epochs": 10,
             "examples": 700 + i * 37}
            for i in range(10)
        ],
    },
    "federated.rounds": {
        "items": [
            {"round": 1, "participating_nodes": 10, "aggregation": "FedAvg", "status": "COMPLETE",
             "started_at": "2026-09-06T17:40:00Z",
             "metrics": {"accuracy": 0.8455, "micro_f1": 0.3712, "macro_f1": 0.049, "hamming_loss": 0.1402}},
            {"round": 2, "participating_nodes": 10, "aggregation": "FedAvg", "status": "COMPLETE",
             "started_at": "2026-09-06T18:00:00Z",
             "metrics": {"accuracy": 0.8719, "micro_f1": 0.3689, "macro_f1": 0.0551, "hamming_loss": 0.1281}},
            {"round": 3, "participating_nodes": 10, "aggregation": "FedAvg", "status": "COMPLETE",
             "started_at": "2026-09-06T18:20:00Z",
             "metrics": {"accuracy": 0.8782, "micro_f1": 0.3923, "macro_f1": 0.0583, "hamming_loss": 0.1218}},
        ]
    },
    "federated.model": {
        "global_model_version": "fl-global-r3",
        "training_round": 3,
        "trained_at": "2026-09-06T18:20:00Z",
        "status": "VALIDATED",
        "aggregation": "FedAvg",
        "clients": 10,
        "server_rounds": 3,
        "honest_metrics": {"accuracy": 0.8782, "micro_f1": 0.3923, "macro_f1": 0.0583, "hamming_loss": 0.1218},
        "caveats": [
            "Macro-F1 is low (0.0583) — minority symptom labels are largely not learned.",
            "Micro-F1 did not improve monotonically across rounds.",
            "Differential privacy and secure aggregation are NOT implemented.",
        ],
    },
    "privacy.policy": {
        "updated_at": "2026-09-05",
        "controls": [
            {"control": "Data minimization (field-level policy)", "status": "IMPLEMENTED", "detail": "Only configured fields leave the local processing step."},
            {"control": "Privacy classification of DB columns", "status": "IMPLEMENTED", "detail": "Each column tagged (identifier / clinical / derived / safe)."},
            {"control": "Pseudonymization (patient_token)", "status": "IMPLEMENTED", "detail": "Deterministic SHA-256(secret + ':' + id); raw patient_id never surfaced."},
            {"control": "Pseudonymization verification", "status": "IMPLEMENTED", "detail": "Automated check that application views carry no raw identifiers."},
            {"control": "Federated learning (data stays local)", "status": "IMPLEMENTED", "detail": "Only model parameters are exchanged; CSV rows never leave the client."},
            {"control": "Differential privacy", "status": "NOT_IMPLEMENTED", "detail": "Conceptual architecture only. Not active."},
            {"control": "Secure aggregation", "status": "NOT_IMPLEMENTED", "detail": "Conceptual architecture only. Not active."},
            {"control": "Update encryption in transit (explicit)", "status": "NOT_IMPLEMENTED", "detail": "Not demonstrated in the prototype."},
        ],
    },
    "privacy.data_flow": {
        "steps": [
            {"step": "Local clinical data", "scope": "Hospital only", "detail": "PostgreSQL: encounters, symptoms, vitals, treatments, labs, imaging."},
            {"step": "Local processing / training", "scope": "Hospital only", "detail": "E1–E12 advisor and Flower client training run against local data."},
            {"step": "Model update", "scope": "Leaves hospital", "detail": "TabNet parameter tensors only — no patient rows, no identifiers."},
            {"step": "Central aggregation", "scope": "Coordinator", "detail": "FedAvg over submitted parameters (Flower server)."},
            {"step": "Global model", "scope": "Shared back", "detail": "Aggregated weights redistributed to hospitals."},
        ],
        "guarantee_note": "Raw patient data never leaves the hospital in this prototype. Only model-update information is exchanged. Stronger cryptographic guarantees (DP, secure aggregation) are not implemented.",
    },
    "privacy.audit": {
        "ran_at": "2026-09-05T09:00:00Z",
        "checks": [
            {"check": "No raw patient_id in application responses", "result": "PASS"},
            {"check": "No raw encounter_id surfaced outside clinical scope", "result": "PASS"},
            {"check": "Surveillance outputs are aggregate-only", "result": "PASS"},
            {"check": "Federated payloads contain parameters only", "result": "PASS"},
            {"check": "Pseudonym reversibility test (should fail to reverse)", "result": "PASS"},
            {"check": "Differential-privacy noise present", "result": "NOT_IMPLEMENTED"},
        ],
        "minimization_matrix": [
            {"field": "patient_id", "local_db": True, "local_processing": True, "transmitted": False, "aggregate_view": False},
            {"field": "patient_token", "local_db": True, "local_processing": True, "transmitted": False, "aggregate_view": True},
            {"field": "age", "local_db": True, "local_processing": True, "transmitted": False, "aggregate_view": True},
            {"field": "symptoms (27)", "local_db": True, "local_processing": True, "transmitted": False, "aggregate_view": True},
            {"field": "vitals", "local_db": True, "local_processing": True, "transmitted": False, "aggregate_view": False},
            {"field": "model parameters", "local_db": False, "local_processing": True, "transmitted": True, "aggregate_view": False},
        ],
    },
    "models.overview": {
        "pipeline": [
            {"stage": "E1", "name": "Patient context", "kind": "data"},
            {"stage": "E2", "name": "Candidate treatments", "kind": "rules"},
            {"stage": "E3", "name": "Clinical eligibility", "kind": "rules"},
            {"stage": "E4", "name": "Configuration enrichment", "kind": "config"},
            {"stage": "E5", "name": "Regional epidemiology", "kind": "context"},
            {"stage": "E6", "name": "Treatment-success model", "kind": "model"},
            {"stage": "E7", "name": "Probability calibration", "kind": "model"},
            {"stage": "E8", "name": "Uncertainty estimation", "kind": "model"},
            {"stage": "E9", "name": "Recovery estimation", "kind": "model"},
            {"stage": "E10", "name": "Risk & complications", "kind": "rules"},
            {"stage": "E11", "name": "SHAP explainability", "kind": "explain"},
            {"stage": "E12", "name": "Weighted ranking", "kind": "rank"},
        ],
        "ranking_weights": {
            "success": 0.4, "uncertainty": 0.15, "recovery": 0.15, "risk": 0.15,
            "availability": 0.05, "guideline": 0.05, "resource": 0.05,
        },
        "note": "E12 ranking weights are project-defined and transparent, not clinically validated.",
    },
    "models.metrics": {
        "treatment_advisor": [
            {"model": "E6 treatment success (RandomForest)", "metric": "Accuracy", "value": "0.81"},
            {"model": "E6 treatment success (RandomForest)", "metric": "ROC-AUC", "value": "0.84"},
            {"model": "E7 calibration", "metric": "Brier score", "value": "0.146"},
            {"model": "E8 uncertainty", "metric": "Interval", "value": "10th–90th percentile (tree spread)"},
            {"model": "E9 recovery time", "metric": "MAE (days)", "value": "1.9"},
            {"model": "E9 recovery time", "metric": "R²", "value": "0.62"},
        ],
        "federated": [
            {"model": "FL global (round 3)", "metric": "Accuracy", "value": "0.8782"},
            {"model": "FL global (round 3)", "metric": "Micro-F1", "value": "0.3923"},
            {"model": "FL global (round 3)", "metric": "Macro-F1", "value": "0.0583"},
            {"model": "FL global (round 3)", "metric": "Hamming loss", "value": "0.1218"},
        ],
        "not_implemented": ["Fairness / subgroup metrics", "Calibration drift monitoring", "Prospective clinical evaluation"],
    },
    "models.versions": {
        "items": [
            {"component": "E6 treatment_success_model.pkl", "version": "rf_v1", "trained": "2026-08-29", "status": "ACTIVE"},
            {"component": "E7 calibration artifact", "version": "sigmoid_v1", "trained": "2026-08-30", "status": "ACTIVE"},
            {"component": "E9 recovery_time_model.pkl", "version": "rf_v1", "trained": "2026-08-31", "status": "ACTIVE"},
            {"component": "FL global model", "version": "fl-global-r3", "trained": "2026-09-06", "status": "ACTIVE"},
            {"component": "FL global model", "version": "fl-global-r2", "trained": "2026-09-06", "status": "SUPERSEDED"},
        ]
    },
}
