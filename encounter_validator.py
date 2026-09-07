import pandas as pd


class EncounterValidationError(ValueError):
    """Raised when an encounter fails validation."""
    pass


class EncounterValidator:

    def __init__(self, tables):
        self.tables = tables

        self.hospitals = set(
            tables["hospital_master"]["hospital_id"].astype(str)
        )

        self.diseases = set(
            tables["disease_master"]["disease_id"].astype(str)
        )

        self.severities = set(
            tables["severity_master"]["severity_id"].astype(str)
        )

        self.symptoms = set(
            tables["symptom_master"]["symptom_id"].astype(str)
        )

        self.treatments = set(
            tables["treatment_master"]["treatment_id"].astype(str)
        )

        self.complications = set(
            tables["complication_master"]["complication_id"].astype(str)
        )

        self.vital_ranges = tables["vital_range_config"].copy()

    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(self, encounter):

        errors = []

        # -------------------------------------------------
        # Required identifiers
        # -------------------------------------------------

        if not encounter.encounter_id:
            errors.append("Missing encounter_id")

        if not encounter.patient_id:
            errors.append("Missing patient_id")

        if encounter.hospital_id not in self.hospitals:
            errors.append(
                f"Invalid hospital_id: {encounter.hospital_id}"
            )

        if encounter.disease_id not in self.diseases:
            errors.append(
                f"Invalid disease_id: {encounter.disease_id}"
            )

        if encounter.severity_id not in self.severities:
            errors.append(
                f"Invalid severity_id: {encounter.severity_id}"
            )

        # -------------------------------------------------
        # Demographics
        # -------------------------------------------------

        age = encounter.demographics.age

        if age is not None and not (0 <= age <= 120):
            errors.append(
                f"Age outside valid range: {age}"
            )

        # -------------------------------------------------
        # General duration checks
        # -------------------------------------------------

        if (
            encounter.symptom_onset_days is not None
            and encounter.symptom_onset_days < 0
        ):
            errors.append(
                f"Negative symptom_onset_days: "
                f"{encounter.symptom_onset_days}"
            )

        if (
            encounter.recovery_days is not None
            and encounter.recovery_days < 0
        ):
            errors.append(
                f"Negative recovery_days: "
                f"{encounter.recovery_days}"
            )

        if (
            encounter.treatment_duration_days is not None
            and encounter.treatment_duration_days < 0
        ):
            errors.append(
                f"Negative treatment_duration_days: "
                f"{encounter.treatment_duration_days}"
            )

        # -------------------------------------------------
        # Vital signs
        # -------------------------------------------------

        errors.extend(
            self._validate_vitals(encounter)
        )

        # -------------------------------------------------
        # Symptoms
        # -------------------------------------------------

        for symptom in encounter.symptoms:

            if symptom.symptom_id not in self.symptoms:
                errors.append(
                    f"Invalid symptom_id: {symptom.symptom_id}"
                )

            if (
                symptom.duration_days is not None
                and symptom.duration_days < 0
            ):
                errors.append(
                    f"Negative symptom duration: "
                    f"{symptom.symptom_id}"
                )

        # -------------------------------------------------
        # Treatments
        # -------------------------------------------------

        for treatment in encounter.treatments:

            if treatment.treatment_id not in self.treatments:
                errors.append(
                    f"Invalid treatment_id: "
                    f"{treatment.treatment_id}"
                )

            if (
                treatment.duration_days is not None
                and treatment.duration_days < 0
            ):
                errors.append(
                    f"Negative treatment duration: "
                    f"{treatment.treatment_id}"
                )

        # -------------------------------------------------
        # Complications
        # -------------------------------------------------

        for complication in encounter.complications:

            if (
                complication.complication_id
                not in self.complications
            ):
                errors.append(
                    f"Invalid complication_id: "
                    f"{complication.complication_id}"
                )

        # -------------------------------------------------
        # Final result
        # -------------------------------------------------

        if errors:
            raise EncounterValidationError(
                "Encounter validation failed:\n - "
                + "\n - ".join(errors)
            )

        return True

    # =====================================================
    # VITAL VALIDATION
    # =====================================================

    def _validate_vitals(self, encounter):

        errors = []

        disease_id = encounter.disease_id
        severity_id = encounter.severity_id

        if not disease_id or not severity_id:
            return errors

        matching = self.vital_ranges[
            (self.vital_ranges["disease_id"] == disease_id)
            & (self.vital_ranges["severity_id"] == severity_id)
        ]

        if matching.empty:
            errors.append(
                f"No vital range configuration found for "
                f"{disease_id} / {severity_id}"
            )
            return errors

        config = matching.iloc[0]

        vitals = encounter.vitals

        checks = [
            (
                "temperature",
                vitals.temperature,
                "temperature_min",
                "temperature_max"
            ),
            (
                "heart_rate",
                vitals.heart_rate,
                "heart_rate_min",
                "heart_rate_max"
            ),
            (
                "respiratory_rate",
                vitals.respiratory_rate,
                "respiratory_rate_min",
                "respiratory_rate_max"
            ),
            (
                "spo2",
                vitals.spo2,
                "spo2_min",
                "spo2_max"
            ),
            (
                "systolic_bp",
                vitals.systolic_bp,
                "systolic_bp_min",
                "systolic_bp_max"
            ),
            (
                "diastolic_bp",
                vitals.diastolic_bp,
                "diastolic_bp_min",
                "diastolic_bp_max"
            ),
        ]

        for name, value, min_col, max_col in checks:

            if value is None:
                continue

            minimum = config[min_col]
            maximum = config[max_col]

            if value < minimum or value > maximum:
                errors.append(
                    f"{name}={value} outside configured "
                    f"range [{minimum}, {maximum}] for "
                    f"{disease_id}/{severity_id}"
                )

        return errors