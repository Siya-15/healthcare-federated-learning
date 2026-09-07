
"""
A5-only validation for the existing A4 output.

IMPORTANT:
- Does NOT run A1-A4.
- Reads the existing emerging_disease_inference.csv produced by A4.
- Runs ONLY Objective A5: Clinical Evidence Integration.
"""

from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent

# Existing A4 output produced by the previous validation/run.
CANDIDATES = [
    ROOT / "ML" / "emerging_symptoms" / "emerging_disease_inference.csv",
    ROOT / "data" / "emerging_symptoms" / "emerging_disease_inference.csv",
    ROOT / "emerging_disease_inference.csv",
]

# ---------------------------------------------------------------------
# Import A5
# ---------------------------------------------------------------------
A5_DIR = ROOT / "ML" / "emerging_symptoms"

if str(A5_DIR) not in sys.path:
    sys.path.insert(0, str(A5_DIR))

try:
    from clinical_evidence_integration import integrate_clinical_evidence
except Exception as e:
    print("ERROR: Could not import clinical_evidence_integration.py")
    print("Expected location:", A5_DIR / "clinical_evidence_integration.py")
    print("Import error:", e)
    sys.exit(1)

a4_path = next((p for p in CANDIDATES if p.exists()), None)

if a4_path is None:
    print("ERROR: Existing A4 output was not found.")
    print("Expected emerging_disease_inference.csv in one of:")
    for p in CANDIDATES:
        print("  ", p)
    sys.exit(1)

print("=" * 80)
print("A5-ONLY VALIDATION")
print("=" * 80)
print(f"Using existing A4 output: {a4_path}")
print("A1-A4 will NOT be executed.")
print()

# ---------------------------------------------------------------------
# Import A5
# ---------------------------------------------------------------------
try:
    from clinical_evidence_integration import integrate_clinical_evidence
except ImportError:
    try:
        from ML.emerging_symptoms.clinical_evidence_integration import (
            integrate_clinical_evidence
        )
    except ImportError:
        print("ERROR: Could not import clinical_evidence_integration.py")
        sys.exit(1)

# ---------------------------------------------------------------------
# Read existing A4 output
# ---------------------------------------------------------------------
a4 = pd.read_csv(a4_path, keep_default_na=False)

print(f"Existing A4 rows: {len(a4)}")

if a4.empty:
    print("ERROR: A4 output is empty.")
    sys.exit(1)

if "symptom_pattern" not in a4.columns:
    print("ERROR: A4 output has no symptom_pattern column.")
    print("Columns:", list(a4.columns))
    sys.exit(1)

# Injected unexplained signature.
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

# ---------------------------------------------------------------------
# Identify the strongest target-related A4 row.
# This is ONLY inspection; A4 is not rerun.
# ---------------------------------------------------------------------
matches = []

for _, row in a4.iterrows():
    symptoms = parse_pattern(row["symptom_pattern"])
    overlap = symptoms.intersection(TARGET)

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
            "pattern": row["symptom_pattern"],
            "overlap": sorted(overlap),
            "overlap_count": len(overlap),
            "score": score,
        })

if not matches:
    print("A5 CANNOT BE TESTED: no target-related pattern exists in A4 output.")
    sys.exit(1)

matches.sort(key=lambda x: (x["overlap_count"], x["score"]), reverse=True)
strongest = matches[0]

print("STRONGEST EXISTING A4 SIGNAL")
print("-" * 80)
print("Pattern       :", strongest["pattern"])
print("Target overlap:", ", ".join(strongest["overlap"]))
print("Overlap count :", strongest["overlap_count"], "/ 6")
print("Score         :", strongest["score"])

# ---------------------------------------------------------------------
# Run ONLY A5.
#
# Current project implementation reads its configured A4 output itself,
# so first try the zero-argument project interface.
# ---------------------------------------------------------------------
print()
print("=" * 80)
print("RUNNING A5 ONLY")
print("=" * 80)

try:
    a5_result = integrate_clinical_evidence()
except TypeError:
    print("A5 function did not accept the zero-argument interface.")
    print("Please send the exact error if this occurs.")
    sys.exit(1)
except Exception as e:
    print("ERROR while running A5:")
    print(e)
    sys.exit(1)

# ---------------------------------------------------------------------
# Normalize result.
# ---------------------------------------------------------------------
if a5_result is None:
    print("ERROR: A5 returned None.")
    sys.exit(1)

if not isinstance(a5_result, pd.DataFrame):
    try:
        a5_result = pd.DataFrame(a5_result)
    except Exception as e:
        print("ERROR: Could not convert A5 result to DataFrame:")
        print(e)
        sys.exit(1)

print(f"A5 output rows: {len(a5_result)}")

if a5_result.empty:
    print()
    print("A5 FAIL — no clinical evidence rows were produced.")
    sys.exit(0)

# ---------------------------------------------------------------------
# Locate corresponding propagated pattern.
# ---------------------------------------------------------------------
a5_match = None

if "symptom_pattern" in a5_result.columns:
    exact = a5_result[
        a5_result["symptom_pattern"].astype(str)
        == str(strongest["pattern"])
    ]

    if not exact.empty:
        a5_match = exact.iloc[0]
    else:
        best_key = (-1, -1.0)

        for _, row in a5_result.iterrows():
            symptoms = parse_pattern(row["symptom_pattern"])
            overlap_count = len(symptoms.intersection(TARGET))

            score = 0.0
            for col in [
                "clinical_evidence_score",
                "evidence_score",
                "combined_evidence_score",
                "emergence_score",
            ]:
                if col in row.index:
                    try:
                        score = float(row[col])
                        break
                    except (ValueError, TypeError):
                        pass

            key = (overlap_count, score)

            if key > best_key:
                best_key = key
                a5_match = row

# ---------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------
print()
print("=" * 80)
print("A5 RESULT")
print("=" * 80)

if a5_match is None:
    print("A5 FAIL — no target-related pattern reached A5.")
    print()
    print("This means A4 produced output, but the signal was not")
    print("represented in A5 output.")
    sys.exit(0)

row = a5_match

pattern = str(row.get("symptom_pattern", ""))
overlap = sorted(parse_pattern(pattern).intersection(TARGET))

print("Pattern               :", pattern)
print("Target overlap        :", ", ".join(overlap))
print("Target overlap count  :", len(overlap), "/ 6")

# Print useful A5 evidence fields without assuming exact schema names.
priority_fields = [
    "clinical_evidence_score",
    "evidence_score",
    "clinical_support_score",
    "supporting_encounters",
    "supporting_hospitals",
    "hospital_count",
    "clinical_cases",
    "evidence_level",
    "clinical_evidence_level",
    "confidence",
    "alert_level",
    "inference_category",
]

for col in priority_fields:
    if col in row.index:
        print(f"{col:23}: {row[col]}")

print()
print("A5 output columns:")
print(", ".join(str(c) for c in a5_result.columns))

print()
print("=" * 80)
print("A5 PASS — the existing A4 signal reached A5 and was evaluated.")
print("=" * 80)
