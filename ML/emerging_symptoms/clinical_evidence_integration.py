
"""
LIGHTWEIGHT A5-ONLY VALIDATION

Does NOT run A1-A4.
Does NOT execute A5's full main(), because main() loads the entire
clinical database into Pandas and can exhaust memory.

Instead:
1. Reads the EXISTING A4 output.
2. Selects the strongest target-related A4 pattern.
3. Dynamically loads the ACTUAL A5 module under a safe alias.
4. Queries PostgreSQL only for encounters matching that A4 pattern.
5. Uses A5's own clinical-evidence functions on that filtered data.
6. Reports whether A5 successfully calculates clinical evidence.

This validates A5 logic without changing A5.
"""

import os

# Prevent NumPy/OpenBLAS from trying to allocate a large thread pool.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from pathlib import Path
import sys
import importlib.util
import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
ML_DIR = ROOT / "ML"
A5_DIR = ML_DIR / "emerging_symptoms"
A5_FILE = A5_DIR / "clinical_evidence_integration.py"
A4_FILE = A5_DIR / "emerging_disease_inference.csv"

TARGET = {
    "Breathlessness",
    "Chest Pain",
    "Diarrhoea",
    "Loss of Appetite",
    "Night Sweats",
    "Runny Nose",
}


def parse_pattern(value):
    return {
        x.strip()
        for x in str(value).split(" + ")
        if x.strip()
    }


def normalize_text(value):
    if pd.isna(value):
        return ""
    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


print("=" * 80)
print("LIGHTWEIGHT A5-ONLY VALIDATION")
print("=" * 80)
print("A1-A4 will NOT be executed.")
print("A5 main() will NOT load the entire database.")
print()

# ---------------------------------------------------------------------
# Check files
# ---------------------------------------------------------------------

if not A4_FILE.exists():
    print("ERROR: Existing A4 output not found:")
    print(A4_FILE)
    sys.exit(1)

if not A5_FILE.exists():
    print("ERROR: A5 module not found:")
    print(A5_FILE)
    sys.exit(1)

# ---------------------------------------------------------------------
# Load existing A4
# ---------------------------------------------------------------------

a4 = pd.read_csv(A4_FILE, keep_default_na=False)

print(f"Existing A4 rows: {len(a4)}")

# Find strongest target-related A4 pattern.
matches = []

for _, row in a4.iterrows():
    pattern = str(row["symptom_pattern"])
    overlap = parse_pattern(pattern).intersection(TARGET)

    if overlap:
        score = 0.0

        for col in [
            "emergence_evidence_score",
            "known_disease_emerging_score",
            "emergence_score",
            "novelty_score",
        ]:
            if col in row.index:
                try:
                    score = float(row[col])
                    break
                except (ValueError, TypeError):
                    pass

        matches.append({
            "row": row,
            "pattern": pattern,
            "overlap": sorted(overlap),
            "count": len(overlap),
            "score": score,
        })

if not matches:
    print("A5 CANNOT BE TESTED: no target-related A4 pattern found.")
    sys.exit(1)

matches.sort(
    key=lambda x: (x["count"], x["score"]),
    reverse=True
)

strongest = matches[0]
a4_row = strongest["row"]

print()
print("STRONGEST EXISTING A4 SIGNAL")
print("-" * 80)
print("Pattern       :", strongest["pattern"])
print("Target overlap:", ", ".join(strongest["overlap"]))
print("Overlap count :", strongest["count"], "/ 6")
print("Score         :", strongest["score"])

# ---------------------------------------------------------------------
# Load ACTUAL A5 module under an alias.
#
# This avoids importing it as "clinical_evidence_integration" from a
# validator with similar project-level import behavior.
# ---------------------------------------------------------------------

print()
print("=" * 80)
print("LOADING ACTUAL A5 MODULE")
print("=" * 80)

spec = importlib.util.spec_from_file_location(
    "a5_actual_module",
    str(A5_FILE)
)

if spec is None or spec.loader is None:
    print("ERROR: Could not create module specification.")
    sys.exit(1)

a5 = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(a5)
except Exception as e:
    print("ERROR loading A5 module:")
    print(type(e).__name__, ":", e)
    sys.exit(1)

print("A5 module loaded successfully.")

# ---------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------

print()
print("=" * 80)
print("QUERYING ONLY RELEVANT CLINICAL DATA")
print("=" * 80)

try:
    # database.py is in project root.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from database import get_engine
    engine = get_engine()

except Exception as e:
    print("ERROR connecting to database:")
    print(type(e).__name__, ":", e)
    sys.exit(1)

# ---------------------------------------------------------------------
# Identify matching encounters for the selected A4 pattern.
# We reproduce A5's exact all-symptoms matching rule, but only query
# relevant symptom rows.
# ---------------------------------------------------------------------

pattern_symptoms = [
    normalize_text(x)
    for x in strongest["pattern"].split(" + ")
    if normalize_text(x)
]

print("Symptoms required by A4 pattern:")
print("  " + ", ".join(pattern_symptoms))

if not pattern_symptoms:
    print("ERROR: A4 pattern contains no symptoms.")
    sys.exit(1)

try:
    symptom_query = text("""
        SELECT
            encounter_id,
            symptom_id,
            symptom_text
        FROM encounter_symptoms
        WHERE LOWER(REPLACE(REPLACE(TRIM(symptom_text), '_', ' '), '-', ' '))
              = ANY(:symptoms)
    """)

    # PostgreSQL ANY needs a list/array; SQLAlchemy will handle this
    # with an expanding IN-style fallback below if necessary.
    placeholders = ", ".join(
        f":s{i}" for i in range(len(pattern_symptoms))
    )

    symptom_query = text(f"""
        SELECT
            encounter_id,
            symptom_id,
            symptom_text
        FROM encounter_symptoms
        WHERE LOWER(REPLACE(REPLACE(TRIM(symptom_text), '_', ' '), '-', ' '))
              IN ({placeholders})
    """)

    params = {
        f"s{i}": symptom
        for i, symptom in enumerate(pattern_symptoms)
    }

    symptoms = pd.read_sql(
        symptom_query,
        engine,
        params=params
    )

except Exception as e:
    print("ERROR querying symptom data:")
    print(type(e).__name__, ":", e)
    sys.exit(1)

print(f"Relevant symptom rows loaded: {len(symptoms):,}")

if symptoms.empty:
    print()
    print("A5 FAIL — no clinical encounters contain the A4 pattern.")
    sys.exit(0)

# Build encounter intersection exactly like A5.
symptoms["normalized_symptom"] = (
    symptoms["symptom_text"].apply(normalize_text)
)

sets = []

for symptom in pattern_symptoms:
    ids = set(
        symptoms.loc[
            symptoms["normalized_symptom"] == symptom,
            "encounter_id"
        ]
    )
    sets.append(ids)

matching_ids = set.intersection(*sets) if sets else set()

print(f"Matching encounters: {len(matching_ids):,}")

if not matching_ids:
    print()
    print("A5 FAIL — A4 pattern reached A5, but no database encounters")
    print("contain ALL symptoms in that A4 pattern.")
    sys.exit(0)

# ---------------------------------------------------------------------
# Load ONLY matching encounters.
# ---------------------------------------------------------------------

id_list = list(matching_ids)

placeholders = ", ".join(
    f":e{i}" for i in range(len(id_list))
)

encounter_query = text(f"""
    SELECT
        encounter_id,
        hospital_id,
        visit_timestamp,
        disease_id,
        temperature,
        heart_rate,
        respiratory_rate,
        systolic_bp,
        diastolic_bp,
        spo2
    FROM patient_encounter
    WHERE encounter_id IN ({placeholders})
""")

params = {
    f"e{i}": value
    for i, value in enumerate(id_list)
}

encounters = pd.read_sql(
    encounter_query,
    engine,
    params=params
)

print(f"Relevant encounter rows loaded: {len(encounters):,}")

# ---------------------------------------------------------------------
# Load ONLY labs for matching encounters.
# ---------------------------------------------------------------------

lab_query = text(f"""
    SELECT
        encounter_id,
        test_code,
        test_name,
        result_value,
        unit,
        reference_range_low,
        reference_range_high,
        abnormal_flag,
        test_timestamp
    FROM encounter_labs
    WHERE encounter_id IN ({placeholders})
""")

labs = pd.read_sql(
    lab_query,
    engine,
    params=params
)

print(f"Relevant lab rows loaded: {len(labs):,}")

# ---------------------------------------------------------------------
# Load ONLY imaging for matching encounters.
# ---------------------------------------------------------------------

imaging_query = text(f"""
    SELECT
        encounter_id,
        imaging_id,
        imaging_name,
        modality,
        body_site,
        finding,
        impression,
        performed_timestamp
    FROM encounter_imaging
    WHERE encounter_id IN ({placeholders})
""")

imaging = pd.read_sql(
    imaging_query,
    engine,
    params=params
)

print(f"Relevant imaging rows loaded: {len(imaging):,}")

# ---------------------------------------------------------------------
# Run A5's OWN encounter-level evidence calculation.
# ---------------------------------------------------------------------

print()
print("=" * 80)
print("RUNNING A5 CLINICAL EVIDENCE CALCULATION")
print("=" * 80)

encounters = encounters.set_index("encounter_id")

labs_by_encounter = {
    encounter_id: group
    for encounter_id, group in labs.groupby("encounter_id")
}

imaging_by_encounter = {
    encounter_id: group
    for encounter_id, group in imaging.groupby("encounter_id")
}

records = []

for encounter_id in matching_ids:

    if encounter_id not in encounters.index:
        continue

    encounter = encounters.loc[encounter_id]

    encounter_labs = labs_by_encounter.get(
        encounter_id,
        pd.DataFrame()
    )

    encounter_imaging = imaging_by_encounter.get(
        encounter_id,
        pd.DataFrame()
    )

    evidence = a5.calculate_encounter_evidence(
        encounter,
        encounter_labs,
        encounter_imaging,
        a4_row["best_matching_disease_id"]
    )

    record = {
        "symptom_pattern": strongest["pattern"],
        "encounter_id": encounter_id,
        "best_matching_disease_id":
            a4_row["best_matching_disease_id"],
        "best_matching_disease":
            a4_row["best_matching_disease"],
        "pathogen_type":
            a4_row.get("pathogen_type", "Unknown"),
        "cross_hospital_score":
            a4_row["cross_hospital_score"],
        "hospitals_affected":
            a4_row["hospitals_affected"],
        "hospital_coverage":
            a4_row["hospital_coverage"],
        "mean_persistence_weeks":
            a4_row["mean_persistence_weeks"],
        "mean_prevalence_growth":
            a4_row["mean_prevalence_growth"],
        "total_anomalous_occurrences":
            a4_row["total_anomalous_occurrences"],
        "inference_category":
            a4_row["inference_category"],
        "alert_level":
            a4_row["alert_level"],
    }

    record.update(evidence)
    records.append(record)

evidence_df = pd.DataFrame(records)

print(f"Encounter-level A5 evidence records: {len(evidence_df):,}")

if evidence_df.empty:
    print()
    print("A5 FAIL — no clinical evidence records were calculated.")
    sys.exit(0)

# ---------------------------------------------------------------------
# Use A5's OWN pattern aggregation function.
# ---------------------------------------------------------------------

final_df = a5.aggregate_pattern_evidence(
    evidence_df
)

print(f"Pattern-level A5 rows: {len(final_df):,}")

if final_df.empty:
    print()
    print("A5 FAIL — pattern aggregation produced no rows.")
    sys.exit(0)

# ---------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------

row = final_df.iloc[0]

print()
print("=" * 80)
print("A5 RESULT")
print("=" * 80)

print("Pattern                    :", row["symptom_pattern"])
print(
    "Target overlap             :",
    ", ".join(
        sorted(
            parse_pattern(row["symptom_pattern"]).intersection(TARGET)
        )
    )
)
print(
    "Clinical evidence score    :",
    row["clinical_evidence_score"]
)
print(
    "Lab support score          :",
    row["lab_support_score"]
)
print(
    "Vital support score        :",
    row["vital_support_score"]
)
print(
    "Imaging support score      :",
    row["imaging_support_score"]
)
print(
    "Disease-specific support   :",
    row["disease_specific_test_support"]
)
print(
    "Abnormal lab rate          :",
    row["abnormal_lab_rate"]
)
print(
    "Combined surveillance score:",
    row["combined_surveillance_score"]
)
print(
    "Clinical support category  :",
    row["clinical_support_category"]
)
print(
    "Final interpretation       :",
    row["final_interpretation"]
)

print()
print("=" * 80)
print("A5 PASS — existing A4 signal was clinically evaluated by A5.")
print("=" * 80)
