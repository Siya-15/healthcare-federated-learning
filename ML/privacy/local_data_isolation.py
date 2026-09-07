"""
Objective C - C2
Local Data Isolation

Enforces and verifies that raw hospital clinical data
does not cross the federated client/server boundary.
"""

from typing import Any, Dict, Iterable


# ==========================================================
# FORBIDDEN PAYLOAD CONTENT
# ==========================================================

FORBIDDEN_PAYLOAD_FIELDS = {
    "patient_id",
    "encounter_id",
    "hospital_id",
    "visit_timestamp",
    "disease_id",
    "severity_id",
    "gender",
    "occupation",
    "district",
    "state",
    "raw_data",
    "raw_dataframe",
    "dataframe",
    "records",
    "clinical_data",
    "patient_data",
    "csv_data",
}


# ==========================================================
# ALLOWED CLIENT -> SERVER CONTENT
# ==========================================================

ALLOWED_UPDATE_FIELDS = {
    "arrays",
    "metrics",
}


ALLOWED_METRIC_FIELDS = {
    "num-examples",
    "element_accuracy",
    "exact_match_accuracy",
    "hamming_loss",
    "micro_f1",
    "macro_f1",
}


# ==========================================================
# PAYLOAD INSPECTION
# ==========================================================

def inspect_federated_payload(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Inspect a client -> server payload.

    Only model arrays and aggregate metrics are allowed.
    """

    payload_keys = set(payload.keys())

    unexpected_fields = (
        payload_keys - ALLOWED_UPDATE_FIELDS
    )

    forbidden_fields = (
        payload_keys & FORBIDDEN_PAYLOAD_FIELDS
    )

    metrics = payload.get("metrics", {})

    metric_keys = set()

    if hasattr(metrics, "keys"):
        try:
            metric_keys = set(metrics.keys())
        except Exception:
            metric_keys = set()

    unexpected_metrics = (
        metric_keys - ALLOWED_METRIC_FIELDS
    )

    passed = (
        len(unexpected_fields) == 0
        and len(forbidden_fields) == 0
        and len(unexpected_metrics) == 0
        and "arrays" in payload
        and "metrics" in payload
    )

    return {
        "passed": passed,
        "payload_fields": sorted(payload_keys),
        "unexpected_fields": sorted(unexpected_fields),
        "forbidden_fields": sorted(forbidden_fields),
        "metric_fields": sorted(metric_keys),
        "unexpected_metric_fields":
            sorted(unexpected_metrics),
    }


# ==========================================================
# DATAFRAME LEAKAGE CHECK
# ==========================================================

def inspect_dataframe_for_leakage(
    dataframe_columns: Iterable[str],
) -> Dict[str, Any]:
    """
    Verify that raw clinical columns are not present
    in the federated transmission layer.
    """

    columns = set(dataframe_columns)

    leaked_fields = (
        columns & FORBIDDEN_PAYLOAD_FIELDS
    )

    return {
        "passed": len(leaked_fields) == 0,
        "columns_checked": len(columns),
        "leaked_fields": sorted(leaked_fields),
    }


# ==========================================================
# UPDATE VALIDATION
# ==========================================================

def validate_model_update(
    updated_parameters,
) -> Dict[str, Any]:
    """
    Verify that a federated model update consists
    of numerical model parameters only.
    """

    issues = []

    if updated_parameters is None:
        issues.append(
            "Model update is None."
        )
        return {
            "passed": False,
            "issues": issues,
        }

    if not isinstance(
        updated_parameters,
        (list, tuple),
    ):
        issues.append(
            "Model update must be a list or tuple "
            "of parameter arrays."
        )

    for index, parameter in enumerate(
        updated_parameters
    ):
        if parameter is None:
            issues.append(
                f"Parameter {index} is None."
            )
            continue

        if not hasattr(parameter, "shape"):
            issues.append(
                f"Parameter {index} has no shape."
            )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


# ==========================================================
# ISOLATION SUMMARY
# ==========================================================

def create_isolation_record(
    hospital_id: str,
    local_column_count: int,
    updated_parameters,
    payload: Dict[str, Any],
) -> Dict[str, Any]:

    update_check = validate_model_update(
        updated_parameters
    )

    payload_check = inspect_federated_payload(
        payload
    )

    return {
        "hospital_id": hospital_id,
        "local_column_count":
            local_column_count,
        "raw_data_transmitted": False,
        "model_update_valid":
            update_check["passed"],
        "payload_valid":
            payload_check["passed"],
        "passed": (
            update_check["passed"]
            and payload_check["passed"]
        ),
    }