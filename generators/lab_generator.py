import random

from models.encounter import LabResult


class LabGenerator:

    def __init__(self, tables):

        self.lab_master = tables["lab_master"].copy()
        self.disease_lab_mapping = tables["disease_lab_mapping"].copy()

        # Clean column names
        self.lab_master.columns = (
            self.lab_master.columns
            .str.strip()
            .str.lower()
        )

        self.disease_lab_mapping.columns = (
            self.disease_lab_mapping.columns
            .str.strip()
            .str.lower()
        )

    # ======================================================
    # GENERATE LAB RESULTS
    # ======================================================

    def generate(self, encounter):

        encounter.labs = []

        disease_id = str(encounter.disease_id)

        mappings = self.disease_lab_mapping[
            self.disease_lab_mapping["disease_id"].astype(str)
            == disease_id
        ]

        if mappings.empty:
            return

        for _, mapping in mappings.iterrows():

            lab_id = str(mapping["lab_id"])

            lab_rows = self.lab_master[
                self.lab_master["lab_id"].astype(str)
                == lab_id
            ]

            if lab_rows.empty:
                continue

            lab = lab_rows.iloc[0]

            frequency = str(
                mapping["frequency"]
            ).strip().lower()

            test_probability = {
                "very common": 0.95,
                "common": 0.85,
                "occasional": 0.60,
                "rare": 0.30
            }.get(frequency, 0.70)

            if random.random() > test_probability:
                continue

            result_type = str(
                lab["result_type"]
            ).strip().lower()

            # ==================================================
            # BINARY TEST
            # ==================================================

            if result_type == "binary":

                result_value, abnormal_flag = (
                    self._generate_binary_result(
                        encounter,
                        mapping
                    )
                )

            # ==================================================
            # NUMERIC TEST
            # ==================================================

            else:

                result_value, abnormal_flag = (
                    self._generate_numeric_result(
                        encounter,
                        lab,
                        mapping
                    )
                )

            # ==================================================
            # CREATE RESULT
            # ==================================================

            result = LabResult(

                test_code=self._clean_test_code(
                    lab["test_code"]
                ),

                test_name=str(
                    lab["lab_name"]
                ),

                result_value=result_value,

                unit=str(
                    lab["unit"]
                ),

                reference_range_low=self._to_float(
                    lab["reference_range_low"]
                ),

                reference_range_high=self._to_float(
                    lab["reference_range_high"]
                ),

                abnormal_flag=abnormal_flag,

                test_timestamp=encounter.visit_timestamp
            )

            encounter.labs.append(result)

    # ======================================================
    # NUMERIC RESULTS
    # ======================================================

    def _generate_numeric_result(
        self,
        encounter,
        lab,
        mapping
    ):

        low = self._to_float(
            lab["reference_range_low"]
        )

        high = self._to_float(
            lab["reference_range_high"]
        )

        if low is None or high is None:
            return None, None

        abnormal_probability = self._to_float(
            mapping["abnormal_probability"]
        )

        severity_effect = str(
            mapping["severity_effect"]
        ).strip().lower()

        is_abnormal = (
            random.random()
            < abnormal_probability
        )

        # ----------------------------------------------
        # Normal result
        # ----------------------------------------------

        if not is_abnormal:

            value = random.uniform(
                low,
                high
            )

            return (
                self._round(value),
                "NORMAL"
            )

        # ----------------------------------------------
        # Disease-specific direction
        # ----------------------------------------------

        direction = self._get_direction(
            encounter.disease_id,
            lab["lab_id"]
        )

        # ----------------------------------------------
        # Severity controls magnitude
        # ----------------------------------------------

        magnitude = {
            "medium": 0.10,
            "high": 0.25
        }.get(
            severity_effect,
            0.10
        )

        normal_range = high - low

        # ----------------------------------------------
        # HIGH
        # ----------------------------------------------

        if direction == "high":

            value = random.uniform(
                high,
                high + normal_range * magnitude
            )

            value = self._apply_physiological_bounds(
                lab["lab_id"],
                value
            )

            return (
                self._round(value),
                "HIGH"
            )

        # ----------------------------------------------
        # LOW
        # ----------------------------------------------

        if direction == "low":

            value = random.uniform(
                low - normal_range * magnitude,
                low
            )

            value = self._apply_physiological_bounds(
                lab["lab_id"],
                value
            )

            return (
                self._round(value),
                "LOW"
            )

        # ----------------------------------------------
        # If direction is unknown
        # ----------------------------------------------

        value = random.choice([
            random.uniform(
                low,
                high
            ),
            random.uniform(
                high,
                high + normal_range * magnitude
            )
        ])

        value = self._apply_physiological_bounds(
            lab["lab_id"],
            value
        )

        flag = (
            "HIGH"
            if value > high
            else "NORMAL"
        )

        return (
            self._round(value),
            flag
        )

    # ======================================================
    # BINARY RESULTS
    # ======================================================

    @staticmethod
    def _generate_binary_result(
        encounter,
        mapping
    ):

        abnormal_probability = LabGenerator._to_float(
            mapping["abnormal_probability"]
        )

        positive = (
            random.random()
            < abnormal_probability
        )

        if positive:

            return 1, "POSITIVE"

        return 0, "NEGATIVE"

    # ======================================================
    # DISEASE / TEST DIRECTION
    # ======================================================

    @staticmethod
    def _get_direction(
        disease_id,
        lab_id
    ):

        disease_id = str(disease_id)
        lab_id = str(lab_id)

        # Dengue
        if disease_id == "D001":

            if lab_id == "L002":
                return "low"       # WBC

            if lab_id == "L003":
                return "low"       # Platelets

            if lab_id in ["L004", "L006", "L007"]:
                return "high"      # CRP / ALT / AST

        # Malaria
        if disease_id == "D002":

            if lab_id == "L002":
                return "low"

            if lab_id in ["L004", "L006", "L007"]:
                return "high"

        # Chikungunya
        if disease_id == "D003":

            if lab_id == "L004":
                return "high"

            if lab_id == "L002":
                return "low"

        # Influenza
        if disease_id == "D004":

            if lab_id == "L004":
                return "high"

            if lab_id == "L014":
                return "low"

        # COVID-19
        if disease_id == "D005":

            if lab_id == "L004":
                return "high"

            if lab_id == "L014":
                return "low"

        # Tuberculosis
        if disease_id == "D006":

            if lab_id in ["L004", "L013"]:
                return "high"

            if lab_id in ["L001", "L002"]:
                return "low"

        # Typhoid
        if disease_id == "D007":

            if lab_id == "L004":
                return "high"

            if lab_id == "L002":
                return "low"

        # Acute Gastroenteritis
        if disease_id == "D008":

            if lab_id == "L004":
                return "high"

            if lab_id == "L009":
                return "high"

            if lab_id == "L005":
                return "high"

        return None

    # ======================================================
    # PHYSIOLOGICAL BOUNDS
    # ======================================================

    @staticmethod
    def _apply_physiological_bounds(
        lab_id,
        value
    ):

        bounds = {

            # Hemoglobin
            "L001": (5.0, 22.0),

            # WBC
            "L002": (0.5, 40.0),

            # Platelets
            "L003": (20.0, 1000.0),

            # CRP
            "L004": (0.0, 300.0),

            # Creatinine
            "L005": (0.2, 15.0),

            # ALT
            "L006": (1.0, 500.0),

            # AST
            "L007": (1.0, 500.0),

            # Glucose
            "L008": (30.0, 600.0),

            # Sodium
            "L009": (110.0, 180.0),

            # Potassium
            "L010": (2.0, 8.0),

            # Bilirubin
            "L011": (0.1, 30.0),

            # Procalcitonin
            "L012": (0.0, 100.0),

            # ESR
            "L013": (0.0, 150.0),

            # SpO2
            "L014": (70.0, 100.0)
        }

        if lab_id in bounds:

            minimum, maximum = bounds[lab_id]

            value = max(
                minimum,
                min(maximum, value)
            )

        return value

    # ======================================================
    # HELPERS
    # ======================================================

    @staticmethod
    def _to_float(value):

        try:
            return float(value)

        except (TypeError, ValueError):

            return None

    @staticmethod
    def _round(value):

        if value is None:
            return None

        return round(value, 2)

    @staticmethod
    def _clean_test_code(value):

        if value is None:
            return ""

        value = str(value).strip()

        if value.lower() == "nan":
            return ""

        return value