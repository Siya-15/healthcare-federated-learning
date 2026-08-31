"""CSV-backed data access.

The Postgres schema is not in this repository, so every read here comes from
the committed CSV artifacts instead. The column set in ml_data_H0XX.csv is a
superset of what the clinical view needs, so no endpoint is degraded by this.

All loads are cached at import-scope via lru_cache: the CSVs are static.
"""

from functools import lru_cache

import pandas as pd

from .config import (
    HOSPITAL_IDS,
    KNOWLEDGE_DIR,
    ML_DATA_DIR,
    ML_DIR,
    SYMPTOM_COLUMNS,
)
from .privacy import pseudonymize

# The knowledge-table CSVs were authored with a UTF-8 BOM.
_BOM = "utf-8-sig"


def _read_knowledge(name: str) -> pd.DataFrame:
    """Read a knowledge-table CSV.

    Several of these were hand-authored and carry stray whitespace inside id
    columns (e.g. "C004 " in disease_complication_mapping.csv), which silently
    breaks id joins. Strip every object column on the way in.
    """
    df = pd.read_csv(KNOWLEDGE_DIR / name, encoding=_BOM)
    df.columns = [c.strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df


@lru_cache(maxsize=1)
def encounters() -> pd.DataFrame:
    """All 10 hospitals' encounters, with a pseudonymous patient_token added.

    encounter_id is classified LINKABLE_IDENTIFIER in the privacy audit, so it
    is never surfaced by the API - patient_token replaces it.
    """
    frames = []
    for hid in HOSPITAL_IDS:
        path = ML_DIR / f"ml_data_{hid}.csv"
        if not path.exists():
            continue
        frames.append(pd.read_csv(path))

    if not frames:
        raise FileNotFoundError(
            f"No ml_data_H0XX.csv files found in {ML_DIR}. "
            "Run prepare_ml_data.py, or restore the committed CSVs."
        )

    df = pd.concat(frames, ignore_index=True)
    df["patient_token"] = df["encounter_id"].map(pseudonymize)
    return df


@lru_cache(maxsize=1)
def _token_index() -> dict:
    df = encounters()
    return {t: i for i, t in enumerate(df["patient_token"])}


def encounter_by_token(token: str):
    idx = _token_index().get(token)
    if idx is None:
        return None
    return encounters().iloc[idx]


@lru_cache(maxsize=1)
def disease_master() -> pd.DataFrame:
    return _read_knowledge("disease_master.csv")


@lru_cache(maxsize=1)
def severity_master() -> pd.DataFrame:
    return _read_knowledge("severity_master.csv")


@lru_cache(maxsize=1)
def treatment_master() -> pd.DataFrame:
    return _read_knowledge("treatment_master.csv")


@lru_cache(maxsize=1)
def hospital_master() -> pd.DataFrame:
    return _read_knowledge("hospital_master.csv")


@lru_cache(maxsize=1)
def treatment_mappings() -> pd.DataFrame:
    return _read_knowledge("disease_treatment_mapping.csv")


@lru_cache(maxsize=1)
def complication_mappings() -> pd.DataFrame:
    return _read_knowledge("disease_complication_mapping.csv")


@lru_cache(maxsize=1)
def complication_master() -> pd.DataFrame:
    return _read_knowledge("complication_master.csv")


# ---------------------------------------------------------------------------
# Precomputed ML outputs (written by the ML/ analysis scripts into ML/data/)
# ---------------------------------------------------------------------------

def _ml_data(name: str) -> pd.DataFrame:
    path = ML_DATA_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@lru_cache(maxsize=1)
def outbreak_surveillance() -> pd.DataFrame:
    return _ml_data("outbreak_surveillance.csv")


@lru_cache(maxsize=1)
def weekly_cases() -> pd.DataFrame:
    return _ml_data("weekly_hospital_cases.csv")


@lru_cache(maxsize=1)
def cross_hospital_patterns() -> pd.DataFrame:
    return _ml_data("cross_hospital_symptom_patterns.csv")


@lru_cache(maxsize=1)
def hospital_pattern_counts() -> pd.DataFrame:
    return _ml_data("hospital_symptom_pattern_counts.csv")


@lru_cache(maxsize=1)
def anomaly_summary() -> pd.DataFrame:
    return _ml_data("hospital_anomaly_summary.csv")


@lru_cache(maxsize=1)
def privacy_audit() -> pd.DataFrame:
    return _ml_data("privacy_audit.csv")


@lru_cache(maxsize=1)
def minimization_matrix() -> pd.DataFrame:
    return _ml_data("data_minimization_matrix.csv")


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def disease_name(disease_id: str) -> str:
    m = disease_master()
    hit = m[m["disease_id"] == disease_id]
    return hit.iloc[0]["disease_name"] if not hit.empty else disease_id


def severity_name(severity_id: str) -> str:
    m = severity_master()
    hit = m[m["severity_id"] == severity_id]
    return hit.iloc[0]["severity_name"] if not hit.empty else severity_id


def treatment_name(treatment_id: str) -> str:
    m = treatment_master()
    hit = m[m["treatment_id"] == treatment_id]
    return hit.iloc[0]["treatment_name"] if not hit.empty else treatment_id


def symptoms_for_row(row) -> list:
    """The symptom columns are one-hot; return the names that are set."""
    return [s for s in SYMPTOM_COLUMNS if s in row.index and int(row[s]) == 1]
