"""
Objective A backend service.

Reads the existing Objective A surveillance outputs produced by
ML/emerging_symptoms and exposes a compact, JSON-safe API model.

Primary output:
    advanced_symptom_novelty.csv (A7)

Fallback:
    emerging_signal_fusion.csv (A6)

Refresh order:
    A3 -> A4 -> A6 -> A7 -> A8

A5 is intentionally NOT executed by this service because the current
clinical_evidence_integration.py in the supplied Objective-A package is
a validation script rather than a standalone pipeline entrypoint. The
existing clinical_evidence_signals.csv is therefore consumed by A6.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ML_DIR = PROJECT_ROOT / "ML"
A_DIR = ML_DIR / "emerging_symptoms"

A7_FILE = A_DIR / "advanced_symptom_novelty.csv"
A6_FILE = A_DIR / "emerging_signal_fusion.csv"
A5_FILE = A_DIR / "clinical_evidence_signals.csv"
A4_FILE = A_DIR / "emerging_disease_inference.csv"
A3_FILE = A_DIR / "cross_hospital_symptom_patterns.csv"
A8_FILE = A_DIR / "continuous_baseline_signals.csv"
A8_STATE_FILE = A_DIR / "baseline_state.json"

SCRIPTS = {
    "A3": A_DIR / "cross_hospital_patterns.py",
    "A4": A_DIR / "emerging_disease_inference.py",
    "A6": A_DIR / "emerging_signal_fusion.py",
    "A7": A_DIR / "advanced_symptom_novelty.py",
    "A8": A_DIR / "continuous_baseline.py",
}

PRIMARY_REQUIRED = [
    "symptom_pattern",
    "a7_novelty_score",
    "a7_novelty_level",
    "a7_interpretation",
]


def _safe(value: Any) -> Any:
    """Convert pandas/numpy values into strict JSON-safe primitives."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, float) and not math.isfinite(value):
        return None

    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()

    return value


def _records(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    if df.empty:
        return []

    return [
        {str(k): _safe(v) for k, v in row.items()}
        for row in df.head(max(1, min(limit, 500))).to_dict(orient="records")
    ]


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False)


def _primary_output() -> tuple[Path, pd.DataFrame, str]:
    """Prefer A7, then A6."""
    if A7_FILE.exists():
        df = _load_csv(A7_FILE)
        if not df.empty and all(c in df.columns for c in PRIMARY_REQUIRED):
            return A7_FILE, df, "A7"

    if A6_FILE.exists():
        df = _load_csv(A6_FILE)
        return A6_FILE, df, "A6"

    raise FileNotFoundError(
        "Objective A output not found. Run the Objective A pipeline first."
    )


def _read_state() -> dict[str, Any]:
    if not A8_STATE_FILE.exists():
        return {}
    try:
        with A8_STATE_FILE.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}

    stat = path.stat()
    return {
        "exists": True,
        "path": str(path),
        "modified_at": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "size_bytes": stat.st_size,
    }


def _run_script(name: str) -> dict[str, Any]:
    script = SCRIPTS[name]

    if not script.exists():
        raise FileNotFoundError(f"{name} script not found: {script}")

    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )

    result = {
        "stage": name,
        "script": str(script),
        "return_code": completed.returncode,
        "success": completed.returncode == 0,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }

    if completed.returncode != 0:
        raise RuntimeError(
            f"Objective A {name} failed.\n"
            f"{completed.stderr[-3000:] or completed.stdout[-3000:]}"
        )

    return result


def refresh_objective_a() -> dict[str, Any]:
    """
    Refresh the existing Objective-A pipeline in dependency order.

    A3 internally performs its hospital-local A2 analysis.
    A4 consumes A3.
    A6 consumes A3/A4/A5.
    A7 consumes A6.
    A8 maintains the continuous baseline state.
    """
    results = []

    for name in ("A3", "A4", "A6", "A7", "A8"):
        results.append(_run_script(name))

    return {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "stages": results,
    }


def build_objective_a_response(
    refresh: bool = False,
    include_records: bool = True,
    record_limit: int = 50,
) -> dict[str, Any]:
    refresh_result = None

    if refresh:
        refresh_result = refresh_objective_a()

    output_path, df, source_stage = _primary_output()

    # Highest-priority Objective-A signals first.
    sort_columns = [
        c for c in
        ["a7_novelty_score", "final_emerging_score", "confidence_score"]
        if c in df.columns
    ]

    if sort_columns:
        df = df.sort_values(sort_columns, ascending=False, na_position="last")

    summary: dict[str, Any] = {
        "objective": "A",
        "title": "Emerging and Atypical Symptom Detection",
        "source_stage": source_stage,
        "output": _file_info(output_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_patterns": int(len(df)),
    }

    if "a7_novelty_level" in df.columns:
        summary["novelty_levels"] = {
            str(k): int(v)
            for k, v in df["a7_novelty_level"]
            .fillna("UNKNOWN")
            .astype(str)
            .value_counts()
            .items()
        }

    if "a7_interpretation" in df.columns:
        summary["interpretations"] = {
            str(k): int(v)
            for k, v in df["a7_interpretation"]
            .fillna("UNKNOWN")
            .astype(str)
            .value_counts()
            .items()
        }

    if "final_alert_level" in df.columns:
        summary["alert_levels"] = {
            str(k): int(v)
            for k, v in df["final_alert_level"]
            .fillna("UNKNOWN")
            .astype(str)
            .value_counts()
            .items()
        }

    if "signal_type" in df.columns:
        summary["signal_types"] = {
            str(k): int(v)
            for k, v in df["signal_type"]
            .fillna("UNKNOWN")
            .astype(str)
            .value_counts()
            .items()
        }

    state = _read_state()
    if state:
        summary["baseline"] = state

    response: dict[str, Any] = {
        "summary": summary,
        "files": {
            "a3": _file_info(A3_FILE),
            "a4": _file_info(A4_FILE),
            "a5": _file_info(A5_FILE),
            "a6": _file_info(A6_FILE),
            "a7": _file_info(A7_FILE),
            "a8": _file_info(A8_FILE),
        },
    }

    if include_records:
        response["records"] = _records(df, record_limit)
    else:
        response["records"] = []

    if refresh_result is not None:
        response["refresh"] = refresh_result

    return response
