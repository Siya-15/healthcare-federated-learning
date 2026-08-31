import pandas as pd


# ==========================================================
# OBJECTIVE A - DATA MINIMIZATION MATRIX
# ==========================================================

DATA_MINIMIZATION = [

    # ------------------------------------------------------
    # IDENTIFIERS
    # ------------------------------------------------------

    {
        "field": "patient_id",
        "category": "DIRECT_IDENTIFIER",
        "B_surveillance": "NOT_REQUIRED",
        "C_federated_learning": "NOT_REQUIRED",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "NOT_REQUIRED",
        "privacy_action":
            "Keep for local clinical record linkage only"
    },

    {
        "field": "encounter_id",
        "category": "LINKABLE_IDENTIFIER",
        "B_surveillance": "LOCAL_ONLY",
        "C_federated_learning": "LOCAL_ONLY",
        "D_anomaly_detection": "LOCAL_ONLY",
        "E_treatment_advisor": "LOCAL_ONLY",
        "privacy_action":
            "Use only for local record linkage"
    },

    # ------------------------------------------------------
    # DEMOGRAPHICS / LOCATION
    # ------------------------------------------------------

    {
        "field": "hospital_id",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "REQUIRED",
        "C_federated_learning": "LOCAL_ONLY",
        "D_anomaly_detection": "LOCAL_ONLY",
        "E_treatment_advisor": "NOT_REQUIRED",
        "privacy_action":
            "Use for hospital-level aggregation"
    },

    {
        "field": "visit_timestamp",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "REQUIRED",
        "C_federated_learning": "NOT_REQUIRED",
        "D_anomaly_detection": "LOCAL_ONLY",
        "E_treatment_advisor": "NOT_REQUIRED",
        "privacy_action":
            "Use locally/for temporal aggregation"
    },

    {
        "field": "age",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "OPTIONAL",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Use only where clinically relevant"
    },

    {
        "field": "gender",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "OPTIONAL",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Use only where analytically required"
    },

    {
        "field": "occupation",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "NOT_REQUIRED",
        "C_federated_learning": "OPTIONAL",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "NOT_REQUIRED",
        "privacy_action":
            "Avoid unnecessary use"
    },

    {
        "field": "district",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "OPTIONAL",
        "C_federated_learning": "NOT_REQUIRED",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "NOT_REQUIRED",
        "privacy_action":
            "Use only for required geographic aggregation"
    },

    {
        "field": "state",
        "category": "QUASI_IDENTIFIER",
        "B_surveillance": "OPTIONAL",
        "C_federated_learning": "NOT_REQUIRED",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "NOT_REQUIRED",
        "privacy_action":
            "Use only for required geographic aggregation"
    },

    # ------------------------------------------------------
    # CLINICAL INFORMATION
    # ------------------------------------------------------

    {
        "field": "clinical_vitals",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "AGGREGATED",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Keep patient-level values local"
    },

    {
        "field": "disease_id",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "AGGREGATED",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Use locally; aggregate for surveillance"
    },

    {
        "field": "severity_id",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "AGGREGATED",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Use locally"
    },

    {
        "field": "symptoms",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "AGGREGATED",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Keep patient-level symptoms local"
    },

    {
        "field": "treatment",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "NOT_REQUIRED",
        "C_federated_learning": "REQUIRED",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Keep treatment records local"
    },

    {
        "field": "recovery_days",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "NOT_REQUIRED",
        "C_federated_learning": "TRAINING_ONLY",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Use only for outcome estimation"
    },

    {
        "field": "complications",
        "category": "SENSITIVE_CLINICAL",
        "B_surveillance": "AGGREGATED",
        "C_federated_learning": "OPTIONAL",
        "D_anomaly_detection": "NOT_REQUIRED",
        "E_treatment_advisor": "REQUIRED",
        "privacy_action":
            "Keep patient-level complication records local"
    },

]


# ==========================================================
# BUILD MATRIX
# ==========================================================

def build_matrix():

    return pd.DataFrame(
        DATA_MINIMIZATION
    )


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    matrix = build_matrix()

    print("=" * 70)
    print("OBJECTIVE A - DATA MINIMIZATION")
    print("=" * 70)

    print(
        "\nData minimization matrix:"
    )

    print(
        matrix.to_string(
            index=False
        )
    )

    output_file = (
        "data_minimization_matrix.csv"
    )

    matrix.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nMatrix saved to: "
        f"{output_file}"
    )