"""Live/objective-facing adapters for the existing ML packages.

A and C are intentionally represented according to what their current
implementations actually provide. No fake live metrics are created.
"""
from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import REPO_ROOT


def _bootstrap():
    import app.bootstrap  # noqa: F401


def objective_d(conn: Connection) -> dict:
    tables = [
        "patient_encounter", "encounter_symptoms", "encounter_treatments",
        "encounter_complications", "encounter_labs", "encounter_imaging",
        "hospital_master", "disease_master", "symptom_master",
        "treatment_master", "severity_master", "disease_treatment_mapping",
        "treatment_contraindication",
    ]
    counts = {}
    for table in tables:
        try:
            counts[table] = int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
        except Exception:
            counts[table] = None
    row = conn.execute(text("SELECT MIN(visit_timestamp), MAX(visit_timestamp), COUNT(*) FROM patient_encounter")).fetchone()
    return {
        "objective": "D",
        "status": "LIVE_DATABASE",
        "source": "Supabase PostgreSQL",
        "table_counts": counts,
        "encounter_date_range": {
            "earliest": row[0].isoformat() if row and row[0] else None,
            "latest": row[1].isoformat() if row and row[1] else None,
            "encounters": int(row[2]) if row else 0,
        },
        "standardized_schema": True,
    }


def objective_b(conn: Connection) -> dict:
    _bootstrap()
    from ML.outbreak_detection_parent.outbreak_detection_child.outbreak_detection import run_foundation
    result = run_foundation()
    assessment = result["assessment"]
    weekly = result["weekly_cases"]
    surveillance = result["surveillance"]
    return {
        "objective": "B",
        "status": "LIVE_ANALYTICS",
        "source": "actual Objective B foundation functions over Supabase-loaded encounters",
        "assessment": assessment,
        "weekly_cases": weekly.tail(100).to_dict("records"),
        "hospital_surveillance": surveillance.tail(100).to_dict("records"),
        "disease_surveillance": result["disease_surveillance"].tail(100).to_dict("records") if hasattr(result["disease_surveillance"], "tail") else result["disease_surveillance"],
    }


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def objective_a(hospital_id: str | None = None) -> dict:
    """Expose actual validated Objective A output artifacts.

    The current A implementation is file-output based; this endpoint therefore
    reads its generated final ML output rather than pretending to retrain A on
    every HTTP request.
    """
    _bootstrap()
    base = REPO_ROOT / "ML" / "emerging_symptoms" / "emerging_symptoms"
    final_file = base / "advanced_symptom_novelty.csv"
    fusion_file = base / "emerging_signal_fusion.csv"
    cross_file = base / "cross_hospital_symptom_patterns.csv"
    df = _read_csv(final_file)
    if hospital_id:
        # The final A6/A7 output is pattern-level and may not have a hospital_id.
        # Use cross-hospital aggregate only for hospital filtering.
        cross = _read_csv(base / "cross_hospital_aggregate_signals.csv")
        cross = cross[cross["hospital_id"].astype(str) == hospital_id]
        return {
            "objective": "A", "status": "ACTUAL_ML_OUTPUT", "source": str(final_file.relative_to(REPO_ROOT)),
            "hospital_id": hospital_id,
            "hospital_pattern_signals": cross.to_dict("records"),
            "note": "Final A6/A7 output is pattern-level; hospital filtering uses A3 aggregate output.",
        }
    return {
        "objective": "A", "status": "ACTUAL_ML_OUTPUT",
        "source": str(final_file.relative_to(REPO_ROOT)),
        "signals": df.replace({float("nan"): None}).to_dict("records"),
        "fusion_rows": int(len(_read_csv(fusion_file))),
        "cross_hospital_rows": int(len(_read_csv(cross_file))),
        "interpretation_boundary": "Pattern novelty/emergence evidence; not definitive pathogen/variant identification.",
    }


def objective_c() -> dict:
    _bootstrap()
    fl_dir = REPO_ROOT / "ML" / "federated_learning" / "federated_learning"
    local_nodes = []
    for i in range(1, 11):
        path = fl_dir / f"ml_data_H{i:03d}.csv"
        if path.exists():
            try:
                n = len(pd.read_csv(path))
            except Exception:
                n = None
            local_nodes.append({"hospital_id": f"H{i:03d}", "local_dataset_present": True, "records": n})
        else:
            local_nodes.append({"hospital_id": f"H{i:03d}", "local_dataset_present": False, "records": None})
    return {
        "objective": "C",
        "status": "FLOWER_IMPLEMENTATION",
        "framework": "Flower",
        "aggregation": "FedAvg",
        "configured_hospitals": 10,
        "configured_rounds": 3,
        "local_data_boundary": "raw clinical records remain local to federated clients",
        "privacy_controls": {
            "differential_privacy": "NOT_IMPLEMENTED",
            "secure_aggregation": "NOT_IMPLEMENTED",
            "update_clipping": "NOT_IMPLEMENTED",
        },
        "nodes": local_nodes,
        "source_files": [
            "ML/federated_learning/federated_learning/flower_client.py",
            "ML/federated_learning/federated_learning/flower_server.py",
            "ML/federated_learning/federated_learning/federated_dataset.py",
        ],
    }


def model_metrics() -> dict:
    """Read metrics embedded in real model artifacts when present."""
    root = REPO_ROOT
    specs = {
        "E6": root / "treatment_success_model.pkl",
        "E7": root / "treatment_probability_calibrator.pkl",
        "E8": root / "treatment_probability_uncertainty.pkl",
        "E9": root / "ML" / "treatment_advisor" / "treatment_advisor" / "recovery_time_model.pkl",
    }
    out = {}
    for name, path in specs.items():
        if not path.exists():
            out[name] = {"artifact_present": False, "path": str(path.relative_to(root))}
            continue
        try:
            import joblib
            artifact = joblib.load(path)
            out[name] = {
                "artifact_present": True,
                "path": str(path.relative_to(root)),
                "metrics": artifact.get("metrics", {}) if isinstance(artifact, dict) else {},
                "config": artifact.get("config", {}) if isinstance(artifact, dict) else {},
            }
        except Exception as exc:
            out[name] = {"artifact_present": True, "load_error": type(exc).__name__}
    return {"source": "actual model artifacts", "models": out}


def privacy_status() -> dict:
    _bootstrap()
    from ML.privacy.local_data_isolation import inspect_federated_payload
    check = inspect_federated_payload({"arrays": [], "metrics": {}})
    return {
        "objective": "C/privacy",
        "status": "IMPLEMENTED_CONTROLS_REPORTED",
        "local_data_isolation_check": check,
        "differential_privacy": "NOT_IMPLEMENTED",
        "secure_aggregation": "NOT_IMPLEMENTED",
        "raw_patient_records_to_server": False,
    }
