"""Create the application schema in Supabase and load seed data.

Usage (from the repo root, with .env present):
    .venv/bin/python backend/seed_supabase.py            # migrate + seed
    .venv/bin/python backend/seed_supabase.py --schema   # migrate only
    .venv/bin/python backend/seed_supabase.py --reset    # DROP app tables, then migrate + seed

Idempotent: re-running upserts reference data and regenerates the synthetic
encounter set + dashboard snapshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
load_dotenv(REPO_ROOT / ".env")

import seed_data as S  # noqa: E402

MIGRATION = REPO_ROOT / "backend" / "migrations" / "002_supabase_app_schema.sql"

APP_TABLES = [
    "advisor_run", "dashboard_snapshot", "encounter_imaging", "encounter_labs",
    "encounter_complications", "encounter_treatments", "encounter_symptoms",
    "patient_encounter", "treatment_config", "treatment_contraindication",
    "disease_treatment_mapping", "treatment_master", "symptom_master",
    "severity_master", "disease_master", "hospital_master",
]

PRIVACY_SECRET = None  # resolved from env at runtime


def _engine():
    import os

    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL missing from .env")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    global PRIVACY_SECRET
    PRIVACY_SECRET = os.getenv("PRIVACY_SECRET", "dev-privacy-secret-change-me")
    return create_engine(url, pool_pre_ping=True, future=True)


def _token(ref: str) -> str:
    return "pt_" + hashlib.sha256(f"{PRIVACY_SECRET}:{ref}".encode()).hexdigest()[:8]


def apply_schema(conn) -> None:
    print(f"Applying {MIGRATION.name} ...")
    sql = MIGRATION.read_text()
    # Strip standalone transaction-control statements; we run inside engine.begin().
    lines = [
        ln for ln in sql.splitlines()
        if ln.strip().upper() not in ("BEGIN;", "COMMIT;")
    ]
    conn.exec_driver_sql("\n".join(lines))


def drop_app_tables(conn) -> None:
    print("Dropping application tables ...")
    for t in APP_TABLES:
        conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))


def seed_reference(conn) -> None:
    print("Seeding reference data ...")
    conn.execute(text("DELETE FROM treatment_config"))
    conn.execute(text("DELETE FROM treatment_contraindication"))
    conn.execute(text("DELETE FROM disease_treatment_mapping"))

    for hid, name, district, state in S.HOSPITALS:
        conn.execute(
            text(
                """INSERT INTO hospital_master (hospital_id, hospital_name, district, state)
                   VALUES (:a,:b,:c,:d)
                   ON CONFLICT (hospital_id) DO UPDATE SET hospital_name = EXCLUDED.hospital_name"""
            ),
            {"a": hid, "b": name, "c": district, "d": state},
        )
    for did, name in S.DISEASES:
        conn.execute(
            text(
                """INSERT INTO disease_master (disease_id, disease_name) VALUES (:a,:b)
                   ON CONFLICT (disease_id) DO UPDATE SET disease_name = EXCLUDED.disease_name"""
            ),
            {"a": did, "b": name},
        )
    for sid, label in S.SEVERITIES:
        conn.execute(
            text(
                """INSERT INTO severity_master (severity_id, severity_label) VALUES (:a,:b)
                   ON CONFLICT (severity_id) DO UPDATE SET severity_label = EXCLUDED.severity_label"""
            ),
            {"a": sid, "b": label},
        )
    for i, name in enumerate(S.SYMPTOMS, start=1):
        conn.execute(
            text(
                """INSERT INTO symptom_master (symptom_id, symptom_name) VALUES (:a,:b)
                   ON CONFLICT (symptom_id) DO UPDATE SET symptom_name = EXCLUDED.symptom_name"""
            ),
            {"a": f"SYM{str(i).zfill(2)}", "b": name},
        )
    for tid, name, desc in S.TREATMENTS:
        conn.execute(
            text(
                """INSERT INTO treatment_master (treatment_id, treatment_name, description)
                   VALUES (:a,:b,:c)
                   ON CONFLICT (treatment_id) DO UPDATE SET treatment_name = EXCLUDED.treatment_name,
                        description = EXCLUDED.description"""
            ),
            {"a": tid, "b": name, "c": desc},
        )

    for did, sid, tid, first, rank in S.DISEASE_TREATMENT_MAPPING:
        conn.execute(
            text(
                """INSERT INTO disease_treatment_mapping
                   (disease_id, severity_id, treatment_id, is_first_line, line_rank)
                   VALUES (:d,:s,:t,:f,:r)"""
            ),
            {"d": did, "s": sid, "t": tid, "f": first, "r": rank},
        )
    for tid, did, stage, reason in S.TREATMENT_CONTRAINDICATION:
        conn.execute(
            text(
                """INSERT INTO treatment_contraindication (treatment_id, disease_id, stage, reason)
                   VALUES (:t,:d,:s,:r)"""
            ),
            {"t": tid, "d": did, "s": stage, "r": reason},
        )

    overrides = {(tid, hid): (a, g, r) for tid, hid, a, g, r in S.TREATMENT_CONFIG_OVERRIDES}
    for hid, *_ in S.HOSPITALS:
        for tid, (avail, guide, tier) in S.TREATMENT_CONFIG_DEFAULTS.items():
            a, g, r = overrides.get((tid, hid), (avail, guide, tier))
            conn.execute(
                text(
                    """INSERT INTO treatment_config
                       (treatment_id, hospital_id, availability, guideline_status, resource_tier)
                       VALUES (:t,:h,:a,:g,:r)
                       ON CONFLICT (treatment_id, hospital_id) DO UPDATE SET
                         availability = EXCLUDED.availability,
                         guideline_status = EXCLUDED.guideline_status,
                         resource_tier = EXCLUDED.resource_tier"""
                ),
                {"t": tid, "h": hid, "a": a, "g": g, "r": r},
            )


def _insert_encounter(conn, e: dict, sx_ids: dict) -> None:
    conn.execute(
        text(
            """INSERT INTO patient_encounter (
                 encounter_id, patient_id, patient_token, hospital_id, visit_timestamp,
                 age, gender, temperature, heart_rate, respiratory_rate, systolic_bp,
                 diastolic_bp, spo2, disease_id, severity_id, discharge_status,
                 symptom_onset_days, source)
               VALUES (:encounter_id, :patient_id, :patient_token, :hospital_id, :visit_timestamp,
                 :age, :gender, :temperature, :heart_rate, :respiratory_rate, :systolic_bp,
                 :diastolic_bp, :spo2, :disease_id, :severity_id, :discharge_status,
                 :symptom_onset_days, :source)
               ON CONFLICT (encounter_id) DO NOTHING"""
        ),
        e,
    )
    for i, name in enumerate(e["_symptoms"]):
        conn.execute(
            text(
                """INSERT INTO encounter_symptoms (encounter_id, symptom_id, symptom_text,
                     symptom_source, is_primary)
                   VALUES (:e,:sid,:txt,'SEED',:primary)"""
            ),
            {"e": e["encounter_id"], "sid": sx_ids.get(name), "txt": name, "primary": i == 0},
        )


def seed_encounters(conn) -> None:
    print("Seeding encounters ...")
    conn.execute(text("DELETE FROM patient_encounter"))  # cascades to children
    sx_ids = {n: f"SYM{str(i).zfill(2)}" for i, n in enumerate(S.SYMPTOMS, start=1)}

    for e in S.CANONICAL_ENCOUNTERS:
        row = {
            "encounter_id": e["encounter_id"],
            "patient_id": f"seed:{e['encounter_id']}",
            "patient_token": e["patient_token"],
            "hospital_id": e["hospital_id"],
            "visit_timestamp": datetime.fromisoformat(e["visit_timestamp"].replace("Z", "+00:00")),
            "age": e["age"], "gender": e["gender"],
            "temperature": e.get("temperature"), "heart_rate": e.get("heart_rate"),
            "respiratory_rate": e.get("respiratory_rate"), "systolic_bp": e.get("systolic_bp"),
            "diastolic_bp": e.get("diastolic_bp"), "spo2": e.get("spo2"),
            "disease_id": e["disease_id"], "severity_id": e["severity_id"],
            "discharge_status": e["discharge_status"], "symptom_onset_days": 3,
            "source": "SEED", "_symptoms": e["symptoms"],
        }
        _insert_encounter(conn, row, sx_ids)

    # Synthetic set: ~4 per hospital, deterministic.
    rng = random.Random(42)
    disease_ids = [d[0] for d in S.DISEASES if d[0] != "D404"]
    disease_symptoms = {
        "D001": ["Fever", "Muscle Pain", "Fatigue", "Sore Throat", "Headache", "Chills"],
        "D002": ["Dry Cough", "Loss of Smell", "Loss of Taste", "Fatigue", "Headache", "Breathlessness"],
        "D003": ["Fever", "Headache", "Joint Pain", "Rash", "Retro-orbital Pain", "Nausea"],
        "D004": ["Fever", "Abdominal Pain", "Diarrhoea", "Loss of Appetite", "Headache"],
        "D005": ["Fever", "Chills", "Sweating", "Headache", "Nausea", "Fatigue"],
        "D006": ["Persistent Cough", "Night Sweats", "Weight Loss", "Fatigue", "Fever"],
        "D007": ["Breathlessness", "Chest Pain", "Persistent Cough", "Fatigue", "Chills"],
        "D008": ["Dry Cough", "Sore Throat", "Runny Nose", "Fatigue", "Chest Pain"],
    }
    genders = ["Male", "Female"]
    statuses = ["Recovered", "Stable", "Referred"]
    now = datetime.now(timezone.utc)
    n = 0
    for hid, *_ in S.HOSPITALS:
        for _ in range(4):
            n += 1
            did = rng.choice(disease_ids)
            sid = rng.choices(["SV001", "SV002", "SV003"], weights=[3, 4, 2])[0]
            pool = disease_symptoms[did]
            k = rng.randint(2, min(5, len(pool)))
            sx = rng.sample(pool, k)
            ref = f"seed:auto:{hid}:{n}"
            eid = "ENC-" + hashlib.sha1(ref.encode()).hexdigest()[:10].upper()
            row = {
                "encounter_id": eid,
                "patient_id": ref,
                "patient_token": _token(ref),
                "hospital_id": hid,
                "visit_timestamp": now - timedelta(days=rng.randint(0, 20), hours=rng.randint(0, 23)),
                "age": rng.randint(16, 88),
                "gender": rng.choice(genders),
                "temperature": round(rng.uniform(36.5, 40.0), 1),
                "heart_rate": rng.randint(66, 120),
                "respiratory_rate": rng.randint(12, 28),
                "systolic_bp": rng.randint(96, 140),
                "diastolic_bp": rng.randint(60, 92),
                "spo2": rng.randint(88, 99),
                "disease_id": did,
                "severity_id": sid,
                "discharge_status": rng.choices(statuses, weights=[5, 4, 1])[0],
                "symptom_onset_days": rng.randint(1, 9),
                "source": "SEED",
                "_symptoms": sx,
            }
            _insert_encounter(conn, row, sx_ids)
    print(f"  {len(S.CANONICAL_ENCOUNTERS)} canonical + {n} synthetic encounters")


def seed_snapshots(conn) -> None:
    print("Seeding dashboard snapshots ...")
    for kind, payload in S.SNAPSHOTS.items():
        conn.execute(
            text(
                """INSERT INTO dashboard_snapshot (kind, payload, generated_at)
                   VALUES (:k, CAST(:p AS jsonb), :g)
                   ON CONFLICT (kind) DO UPDATE SET payload = EXCLUDED.payload,
                        generated_at = EXCLUDED.generated_at"""
            ),
            {"k": kind, "p": json.dumps(payload), "g": datetime.now(timezone.utc)},
        )
    print(f"  {len(S.SNAPSHOTS)} snapshots")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", action="store_true", help="apply migration only")
    ap.add_argument("--reset", action="store_true", help="drop app tables first")
    args = ap.parse_args()

    engine = _engine()
    with engine.begin() as conn:
        if args.reset:
            drop_app_tables(conn)
        apply_schema(conn)
        if args.schema:
            print("Schema applied. Skipping seed (--schema).")
            return
        seed_reference(conn)
        seed_encounters(conn)
        seed_snapshots(conn)
    print("\nDone. Start the API with:")
    print("  .venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000")


if __name__ == "__main__":
    main()
