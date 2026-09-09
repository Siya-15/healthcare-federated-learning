from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

B_DIR = (
    PROJECT_ROOT
    / "ML"
    / "outbreak_detection_parent"
    / "outbreak_detection_child"
)

B13_SCRIPT = B_DIR / "continuous_update_pipeline.py"


OUTPUTS = {
    "weekly_hospital_cases": B_DIR / "weekly_hospital_cases.csv",
    "symptom_surveillance": B_DIR / "symptom_surveillance.csv",
    "historical_baseline": B_DIR / "symptom_historical_baseline.csv",
    "anomaly": B_DIR / "symptom_anomaly_detection.csv",
    "temporal": B_DIR / "temporal_acceleration.csv",
    "persistence": B_DIR / "symptom_persistence_detection.csv",
    "spatial": B_DIR / "spatial_propagation.csv",
    "objective_a_integration": B_DIR / "objective_a_integration.csv",
    "severity": B_DIR / "severity_burden.csv",
    "risk": B_DIR / "outbreak_risk_engine.csv",
    "alerts": B_DIR / "alert_engine.csv",
    "alerts_latest": B_DIR / "alert_engine_latest.csv",
    "active_alerts": B_DIR / "active_alerts.csv",
    "explainability": B_DIR / "explainability_engine.csv",
    "explainability_latest": B_DIR / "explainability_latest.csv",
    "system_state": B_DIR / "b13_system_state.csv",
    "update_log": B_DIR / "b13_update_log.csv",
}


def _safe_value(value: Any):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return value


def _records(df: pd.DataFrame, limit: int = 100):
    if df.empty:
        return []

    df = df.head(limit)

    result = []

    for row in df.to_dict(orient="records"):
        result.append(
            {
                str(key): _safe_value(value)
                for key, value in row.items()
            }
        )

    return result


def _read_csv(name: str) -> pd.DataFrame:
    path = OUTPUTS[name]

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _latest(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Try common date/week columns without assuming a fixed schema.
    for column in ["week", "date", "timestamp", "generated_at"]:
        if column in df.columns:
            converted = pd.to_datetime(
                df[column],
                errors="coerce"
            )

            if converted.notna().any():
                latest_value = converted.max()
                return df[converted == latest_value].copy()

    # If there is no temporal column, use the final records.
    return df.tail(100).copy()


def _run_b13():
    """
    Execute the existing project B13 pipeline.

    We intentionally do not import or unpack internal B functions here.
    B13 is the existing orchestration layer and already knows how its
    B1-B12 functions communicate with one another.
    """

    if not B13_SCRIPT.exists():
        raise FileNotFoundError(
            f"B13 pipeline not found: {B13_SCRIPT}"
        )

    completed = subprocess.run(
        [sys.executable, str(B13_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=int(
            os.getenv(
                "B13_TIMEOUT_SECONDS",
                "900"
            )
        ),
    )

    if completed.returncode != 0:
        error_text = completed.stderr.strip()

        if not error_text:
            error_text = completed.stdout.strip()

        raise RuntimeError(
            "Objective B13 failed:\n"
            + error_text[-5000:]
        )

    return {
        "executed": True,
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-5000:],
        "stderr_tail": completed.stderr[-5000:],
    }


def build_objective_b_response(
    refresh: bool = False,
    include_records: bool = False,
    record_limit: int = 100,
):

    execution = None

    if refresh:
        execution = _run_b13()

    weekly = _read_csv("weekly_hospital_cases")
    symptoms = _read_csv("symptom_surveillance")
    baseline = _read_csv("historical_baseline")
    anomaly = _read_csv("anomaly")
    temporal = _read_csv("temporal")
    persistence = _read_csv("persistence")
    spatial = _read_csv("spatial")
    a_integration = _read_csv("objective_a_integration")
    severity = _read_csv("severity")
    risk = _read_csv("risk")
    alerts = _read_csv("alerts")
    alerts_latest = _read_csv("alerts_latest")
    active_alerts = _read_csv("active_alerts")
    explainability = _read_csv("explainability")
    explainability_latest = _read_csv("explainability_latest")
    state = _read_csv("system_state")
    update_log = _read_csv("update_log")

    # Prefer explicit latest output files when they exist.
    latest_alerts = (
        alerts_latest
        if not alerts_latest.empty
        else _latest(alerts)
    )

    latest_explanations = (
        explainability_latest
        if not explainability_latest.empty
        else _latest(explainability)
    )

    latest_risk = _latest(risk)

    summary = {
        "weekly_records": len(weekly),
        "symptom_surveillance_records": len(symptoms),
        "historical_baseline_records": len(baseline),
        "anomaly_records": len(anomaly),
        "temporal_records": len(temporal),
        "persistence_records": len(persistence),
        "spatial_records": len(spatial),
        "objective_a_integration_records": len(a_integration),
        "severity_records": len(severity),
        "risk_records": len(risk),
        "alert_records": len(alerts),
        "active_alert_count": len(active_alerts),
        "explainability_records": len(explainability),
    }

    # Alert-level summary from actual B11 output.
    if (
        not latest_alerts.empty
        and "alert_level" in latest_alerts.columns
    ):
        counts = (
            latest_alerts["alert_level"]
            .fillna("UNKNOWN")
            .astype(str)
            .value_counts()
            .to_dict()
        )

        summary["latest_alert_counts"] = {
            str(key): int(value)
            for key, value in counts.items()
        }

    # Latest system state.
    if not state.empty:
        row = state.tail(1).iloc[0]

        summary["system_state"] = {
            str(key): _safe_value(value)
            for key, value in row.items()
        }

    # Latest update record.
    if not update_log.empty:
        row = update_log.tail(1).iloc[0]

        summary["last_update"] = {
            str(key): _safe_value(value)
            for key, value in row.items()
        }

    response = {
        "objective": "B",
        "objective_name": "Epidemic / Pandemic Detection",
        "status": "COMPLETED",
        "engine": "ACTUAL_B13_B1_B12_PIPELINE",
        "data_source": "Supabase PostgreSQL",
        "pipeline": [
            "B1",
            "B2",
            "B3",
            "B4",
            "B5",
            "B6",
            "B7",
            "B8",
            "B9",
            "B10",
            "B11",
            "B12",
        ],
        "execution": execution,
        "summary": summary,
        "latest": {
            "risk": _records(
                latest_risk,
                record_limit
            ),
            "alerts": _records(
                latest_alerts,
                record_limit
            ),
            "explanations": _records(
                latest_explanations,
                record_limit
            ),
            "active_alerts": _records(
                active_alerts,
                record_limit
            ),
        },
        "limitations": [
            "Prototype surveillance system; not clinically validated outbreak prediction.",
            "Alert levels are analytical early-warning signals.",
            "The system does not independently prove an epidemic or pandemic.",
        ],
        "disclaimer": (
            "Objective B provides project-level analytical surveillance "
            "and early-warning signals. It does not independently diagnose "
            "disease, prove an outbreak, forecast a pandemic, or establish causality."
        ),
    }

    if include_records:
        response["records"] = {
            "weekly_hospital_cases": _records(
                weekly,
                record_limit
            ),
            "symptom_surveillance": _records(
                symptoms,
                record_limit
            ),
            "historical_baseline": _records(
                baseline,
                record_limit
            ),
            "anomaly": _records(
                anomaly,
                record_limit
            ),
            "temporal": _records(
                temporal,
                record_limit
            ),
            "persistence": _records(
                persistence,
                record_limit
            ),
            "spatial": _records(
                spatial,
                record_limit
            ),
            "objective_a_integration": _records(
                a_integration,
                record_limit
            ),
            "severity": _records(
                severity,
                record_limit
            ),
            "risk": _records(
                risk,
                record_limit
            ),
            "alerts": _records(
                alerts,
                record_limit
            ),
            "explainability": _records(
                explainability,
                record_limit
            ),
        }

    return response