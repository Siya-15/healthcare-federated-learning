-- ============================================================
-- Migration 001: Complete Encounter Persistence
-- Objective D — Standardized Local Clinical Database
-- ============================================================

BEGIN;

-- ============================================================
-- 1. PATIENT ENCOUNTER
-- ============================================================

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS parent_encounter_id VARCHAR(50);

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS treatment_duration_days INTEGER;

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS readmitted_within_30_days BOOLEAN;

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS follow_up_status VARCHAR(50);

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS complication_count INTEGER DEFAULT 0;

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS admission_required BOOLEAN;

ALTER TABLE patient_encounter
    ADD COLUMN IF NOT EXISTS referral_required BOOLEAN;


-- ============================================================
-- 2. ENCOUNTER SYMPTOMS
-- ============================================================

ALTER TABLE encounter_symptoms
    ADD COLUMN IF NOT EXISTS severity VARCHAR(50);

ALTER TABLE encounter_symptoms
    ADD COLUMN IF NOT EXISTS duration_days INTEGER;

ALTER TABLE encounter_symptoms
    ADD COLUMN IF NOT EXISTS frequency VARCHAR(50);

ALTER TABLE encounter_symptoms
    ADD COLUMN IF NOT EXISTS progression VARCHAR(50);

ALTER TABLE encounter_symptoms
    ADD COLUMN IF NOT EXISTS onset_timestamp TIMESTAMP;


-- ============================================================
-- 3. ENCOUNTER TREATMENTS
-- ============================================================

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS dose NUMERIC;

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS dose_unit VARCHAR(30);

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS frequency VARCHAR(50);

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS duration_days INTEGER;

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS start_timestamp TIMESTAMP;

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS end_timestamp TIMESTAMP;

ALTER TABLE encounter_treatments
    ADD COLUMN IF NOT EXISTS adverse_effect TEXT;


-- ============================================================
-- 4. ENCOUNTER COMPLICATIONS
-- ============================================================

ALTER TABLE encounter_complications
    ADD COLUMN IF NOT EXISTS severity_id VARCHAR(10);

ALTER TABLE encounter_complications
    ADD COLUMN IF NOT EXISTS resolution_timestamp TIMESTAMP;


-- ============================================================
-- 5. DEFAULT / BACKFILL SAFE VALUES
-- ============================================================

UPDATE patient_encounter
SET complication_count = 0
WHERE complication_count IS NULL;


COMMIT;