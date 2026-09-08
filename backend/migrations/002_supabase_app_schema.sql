-- ============================================================
-- Migration 002: Application backend schema (Supabase / PostgreSQL)
-- ============================================================
-- Creates every table the multi-portal frontend needs through the
-- FastAPI service. Safe to run repeatedly (IF NOT EXISTS / idempotent).
--
-- Layout:
--   * Reference / master + advisor-config tables  (structured)
--   * patient_encounter + 6 child tables          (structured, column-
--       compatible with the ML side's database_writer.py so a later
--       simulation run can share this database)
--   * advisor_run                                 (structured audit log
--       of every E13 treatment-advisor output)
--   * dashboard_snapshot                          (JSONB, keyed by "kind"
--       -- holds the read-only prototype outputs for the Surveillance /
--       Federated / Privacy / AI-Ops portals; the payload matches the
--       API response contract 1:1)
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- Reference / master data (Objective D + loader.py vocab)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hospital_master (
    hospital_id   VARCHAR(10) PRIMARY KEY,
    hospital_name VARCHAR(120) NOT NULL,
    district      VARCHAR(80),
    state         VARCHAR(80)
);

CREATE TABLE IF NOT EXISTS disease_master (
    disease_id   VARCHAR(10) PRIMARY KEY,
    disease_name VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS severity_master (
    severity_id    VARCHAR(10) PRIMARY KEY,
    severity_label VARCHAR(40) NOT NULL
);

CREATE TABLE IF NOT EXISTS symptom_master (
    symptom_id   VARCHAR(10) PRIMARY KEY,
    symptom_name VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS treatment_master (
    treatment_id   VARCHAR(10) PRIMARY KEY,
    treatment_name VARCHAR(200) NOT NULL,
    description    TEXT
);

-- E2 candidate generation: which treatments are options for a disease
-- (optionally severity-specific).
CREATE TABLE IF NOT EXISTS disease_treatment_mapping (
    id           BIGSERIAL PRIMARY KEY,
    disease_id   VARCHAR(10) NOT NULL,
    severity_id  VARCHAR(10),
    treatment_id VARCHAR(10) NOT NULL,
    is_first_line BOOLEAN DEFAULT FALSE,
    line_rank    INTEGER DEFAULT 5
);

-- E3 clinical eligibility: hard exclusions applied before ranking.
CREATE TABLE IF NOT EXISTS treatment_contraindication (
    id           BIGSERIAL PRIMARY KEY,
    treatment_id VARCHAR(10) NOT NULL,
    disease_id   VARCHAR(10),
    stage        VARCHAR(10) DEFAULT 'E3',
    reason       TEXT NOT NULL
);

-- E4 configuration enrichment: per-hospital availability / guideline /
-- resource posture for each treatment.
CREATE TABLE IF NOT EXISTS treatment_config (
    id               BIGSERIAL PRIMARY KEY,
    treatment_id     VARCHAR(10) NOT NULL,
    hospital_id      VARCHAR(10) NOT NULL,
    availability      VARCHAR(20)  DEFAULT 'AVAILABLE',   -- AVAILABLE | LIMITED | UNAVAILABLE
    guideline_status  VARCHAR(30)  DEFAULT 'UNKNOWN',     -- PROJECT_SUPPORTED | PROJECT_SUPPORTED_REVIEW | NOT_SUPPORTED | UNKNOWN
    resource_tier     VARCHAR(10)  DEFAULT 'MEDIUM',      -- LOW | MEDIUM | HIGH
    UNIQUE (treatment_id, hospital_id)
);

-- ------------------------------------------------------------
-- Clinical encounter tables (column-compatible with database_writer.py)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_encounter (
    encounter_id              VARCHAR(50) PRIMARY KEY,
    patient_id                VARCHAR(64) NOT NULL,
    patient_token             VARCHAR(64) NOT NULL,
    hospital_id               VARCHAR(10) NOT NULL REFERENCES hospital_master(hospital_id),
    parent_encounter_id       VARCHAR(50),
    visit_timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(),
    age                       INTEGER,
    gender                    VARCHAR(20),
    occupation                VARCHAR(80),
    district                  VARCHAR(80),
    state                     VARCHAR(80),
    temperature               NUMERIC,
    heart_rate                INTEGER,
    respiratory_rate          INTEGER,
    systolic_bp               INTEGER,
    diastolic_bp              INTEGER,
    spo2                      INTEGER,
    disease_id                VARCHAR(10),
    severity_id               VARCHAR(10),
    admission_status          VARCHAR(30),
    visit_type                VARCHAR(30),
    symptom_onset_days        INTEGER,
    travel_history            VARCHAR(160),
    vaccination_status        VARCHAR(30),
    discharge_status          VARCHAR(30),
    recovery_days             INTEGER,
    treatment_duration_days   INTEGER,
    readmitted_within_30_days BOOLEAN,
    follow_up_status          VARCHAR(50),
    complication_count        INTEGER DEFAULT 0,
    admission_required        BOOLEAN,
    referral_required         BOOLEAN,
    source                    VARCHAR(20) DEFAULT 'APP',   -- APP | SIMULATION
    created_at                TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_encounter_hospital ON patient_encounter (hospital_id);
CREATE INDEX IF NOT EXISTS ix_encounter_visit    ON patient_encounter (visit_timestamp DESC);

CREATE TABLE IF NOT EXISTS encounter_symptoms (
    id             BIGSERIAL PRIMARY KEY,
    encounter_id   VARCHAR(50) NOT NULL REFERENCES patient_encounter(encounter_id) ON DELETE CASCADE,
    symptom_id     VARCHAR(10),
    symptom_text   VARCHAR(120),
    symptom_source VARCHAR(20),
    is_primary     BOOLEAN,
    onset_stage    VARCHAR(30),
    severity       VARCHAR(50),
    duration_days  INTEGER,
    frequency      VARCHAR(50),
    progression    VARCHAR(50),
    onset_timestamp TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_symptoms_encounter ON encounter_symptoms (encounter_id);

CREATE TABLE IF NOT EXISTS encounter_treatments (
    id                BIGSERIAL PRIMARY KEY,
    encounter_id      VARCHAR(50) NOT NULL REFERENCES patient_encounter(encounter_id) ON DELETE CASCADE,
    treatment_id      VARCHAR(10),
    treatment_sequence INTEGER,
    dose              NUMERIC,
    dose_unit         VARCHAR(30),
    frequency         VARCHAR(50),
    duration_days     INTEGER,
    start_timestamp   TIMESTAMP,
    end_timestamp     TIMESTAMP,
    adverse_effect    TEXT,
    recommended_by_ai BOOLEAN,
    administered      BOOLEAN,
    treatment_notes   TEXT,
    accepted_by_doctor BOOLEAN,
    treatment_origin  VARCHAR(30)
);
CREATE INDEX IF NOT EXISTS ix_treatments_encounter ON encounter_treatments (encounter_id);

CREATE TABLE IF NOT EXISTS encounter_complications (
    id                   BIGSERIAL PRIMARY KEY,
    encounter_id         VARCHAR(50) NOT NULL REFERENCES patient_encounter(encounter_id) ON DELETE CASCADE,
    complication_id      VARCHAR(10),
    identified_timestamp TIMESTAMP,
    resolved             BOOLEAN,
    severity_id          VARCHAR(10),
    resolution_timestamp TIMESTAMP,
    notes                TEXT
);
CREATE INDEX IF NOT EXISTS ix_complications_encounter ON encounter_complications (encounter_id);

CREATE TABLE IF NOT EXISTS encounter_labs (
    id                   BIGSERIAL PRIMARY KEY,
    encounter_id         VARCHAR(50) NOT NULL REFERENCES patient_encounter(encounter_id) ON DELETE CASCADE,
    test_code            VARCHAR(30),
    test_name            VARCHAR(120),
    result_value         NUMERIC,
    unit                 VARCHAR(30),
    reference_range_low   NUMERIC,
    reference_range_high  NUMERIC,
    abnormal_flag        VARCHAR(20),
    test_timestamp       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_labs_encounter ON encounter_labs (encounter_id);

CREATE TABLE IF NOT EXISTS encounter_imaging (
    id                  BIGSERIAL PRIMARY KEY,
    encounter_id        VARCHAR(50) NOT NULL REFERENCES patient_encounter(encounter_id) ON DELETE CASCADE,
    imaging_id          VARCHAR(20),
    imaging_name        VARCHAR(120),
    modality            VARCHAR(40),
    body_site           VARCHAR(80),
    finding             TEXT,
    impression          TEXT,
    performed_timestamp TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_imaging_encounter ON encounter_imaging (encounter_id);

-- ------------------------------------------------------------
-- Application: treatment-advisor audit log (every E13 output)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS advisor_run (
    id                BIGSERIAL PRIMARY KEY,
    encounter_id      VARCHAR(50),
    hospital_id       VARCHAR(10),
    requested_by_role VARCHAR(40),
    engine            VARCHAR(40),              -- ml_pipeline | heuristic_fallback
    advisor_status    VARCHAR(30),              -- COMPLETED | NO_CANDIDATES
    top_treatment_id  VARCHAR(10),
    output            JSONB NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_advisor_run_hospital ON advisor_run (hospital_id, created_at DESC);

-- ------------------------------------------------------------
-- Application: read-only prototype dashboard payloads
--   kind examples:
--     surveillance.overview | surveillance.alerts |
--     surveillance.emerging_symptoms | surveillance.trends |
--     federated.network | federated.rounds | federated.model |
--     privacy.policy | privacy.data_flow | privacy.audit |
--     models.overview | models.metrics | models.versions |
--     doctor.dashboard
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dashboard_snapshot (
    kind         VARCHAR(60) PRIMARY KEY,
    payload      JSONB NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT now()
);

COMMIT;
