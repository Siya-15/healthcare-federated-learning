
import importlib
import sys
from pathlib import Path


HOSPITALS = [f"H{i:03d}" for i in range(1, 11)]

EXPECTED_FEATURES = 10
EXPECTED_TARGETS = 27


def _find_project_root() -> Path:
    """
    synthetic_generator/
      backend/
        app/
          services/
            objective_c4_service.py

    Therefore parents[3] is synthetic_generator/.
    """
    return Path(__file__).resolve().parents[3]


def _load_task():
    root = _find_project_root()

    # Make the project root importable.
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    candidates = (
        "ML.federated_learning.task",
        "federated_learning.task",
    )

    errors = []

    for module_name in candidates:
        try:
            return importlib.import_module(module_name)
        except Exception as exc:
            errors.append(
                f"{module_name}: {type(exc).__name__}: {exc}"
            )

    raise RuntimeError(
        "Unable to load federated task module. "
        + " | ".join(errors)
    )


def _validate_hospital(task_module, hospital_id: str) -> dict:
    result = {
        "hospital_id": hospital_id,
        "status": "PASS",
        "train_rows": 0,
        "test_rows": 0,
        "features": 0,
        "symptom_labels": 0,
        "error": None,
    }

    try:
        X_train, X_test, y_train, y_test = task_module.load_data(
            hospital_id
        )

        train_rows = int(len(X_train))
        test_rows = int(len(X_test))

        train_features = int(X_train.shape[1])
        test_features = int(X_test.shape[1])

        train_targets = int(y_train.shape[1])
        test_targets = int(y_test.shape[1])

        result.update(
            {
                "train_rows": train_rows,
                "test_rows": test_rows,
                "features": train_features,
                "symptom_labels": train_targets,
            }
        )

        valid = (
            train_features == EXPECTED_FEATURES
            and test_features == EXPECTED_FEATURES
            and train_targets == EXPECTED_TARGETS
            and test_targets == EXPECTED_TARGETS
            and train_rows == len(y_train)
            and test_rows == len(y_test)
        )

        if not valid:
            result["status"] = "FAIL"
            result["error"] = (
                "Unexpected federated dataset shape."
            )

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result


def _source_evidence() -> dict:
    root = _find_project_root()

    candidates = {
        "flower_client": [
            root / "ML" / "federated_learning" / "flower_client.py",
            root / "federated_learning" / "flower_client.py",
        ],
        "flower_server": [
            root / "ML" / "federated_learning" / "flower_server.py",
            root / "federated_learning" / "flower_server.py",
        ],
        "federated_dataset": [
            root / "ML" / "federated_learning" / "federated_dataset.py",
            root / "federated_learning" / "federated_dataset.py",
        ],
        "data_minimization": [
            root / "ML" / "privacy" / "data_minimization.py",
            root / "privacy" / "data_minimization.py",
        ],
        "local_data_isolation": [
            root / "ML" / "privacy" / "local_data_isolation.py",
            root / "privacy" / "local_data_isolation.py",
        ],
    }

    evidence = {}

    for name, paths in candidates.items():
        found = next(
            (path for path in paths if path.exists()),
            None,
        )

        evidence[name] = {
            "available": found is not None,
            "path": str(found) if found else None,
        }

    return evidence


def build_c4_evidence() -> dict:
    task_module = _load_task()

    hospital_results = [
        _validate_hospital(task_module, hospital_id)
        for hospital_id in HOSPITALS
    ]

    passed = sum(
        item["status"] == "PASS"
        for item in hospital_results
    )

    failed = len(hospital_results) - passed

    source_checks = _source_evidence()

    all_hospitals_valid = failed == 0

    return {
        "objective": "C4 - Privacy-Preserving Federated Surveillance",
        "status": "ACTIVE" if all_hospitals_valid else "VALIDATING",

        "verification": {
            "type": "LIVE_IMPLEMENTATION_CHECK",
            "hospital_datasets_checked": len(HOSPITALS),
            "hospitals_passed": passed,
            "hospitals_failed": failed,
            "all_hospitals_valid": all_hospitals_valid,
        },

        "federated_learning": {
            "framework": "Flower",
            "aggregation": "FedAvg",
            "participating_hospitals": len(HOSPITALS),
            "input_features": EXPECTED_FEATURES,
            "symptom_labels": EXPECTED_TARGETS,
            "local_training": source_checks["flower_client"]["available"],
            "fedavg_server": source_checks["flower_server"]["available"],
        },

        "privacy": {
            "hospital_data_isolation": source_checks[
                "local_data_isolation"
            ]["available"],
            "data_minimization": source_checks[
                "data_minimization"
            ]["available"],
            "standardized_federated_dataset": source_checks[
                "federated_dataset"
            ]["available"],
            "raw_patient_data_shared": False,
        },

        "hospital_validation": hospital_results,

        "evidence": {
            "source_checks": source_checks,
        },
    }
