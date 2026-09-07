import random
from datetime import timedelta

from models.encounter import Symptom


class SymptomGenerator:

    def __init__(self, tables):

        self.symptom_mapping = tables["disease_symptom_mapping"]
        self.symptom_master = tables["symptom_master"]

        # --------------------------------------------------
        # Probability for optional symptoms
        # --------------------------------------------------

        self.frequency_probability = {
            "Rare": 0.20,
            "Occasional": 0.45,
            "Common": 0.75,
            "Very Common": 0.95
        }

        # --------------------------------------------------
        # Severity Multipliers
        # --------------------------------------------------

        self.severity_multiplier = {
            "SV001": 0.80,      # Mild
            "SV002": 1.00,      # Moderate
            "SV003": 1.25       # Severe
        }

        # --------------------------------------------------
        # Symptom progression patterns
        # --------------------------------------------------

        self.progression_by_severity = {
            "SV001": ["Stable", "Improving"],
            "SV002": ["Stable", "Worsening"],
            "SV003": ["Worsening", "Stable"]
        }

    # ======================================================
    # GET SYMPTOMS
    # ======================================================

    def get_symptoms(self, disease_id):

        return self.symptom_mapping[
            self.symptom_mapping["disease_id"] == disease_id
        ]

    # ======================================================
    # GET SYMPTOM
    # ======================================================

    def get_symptom(self, mapping_row, encounter):

        master = self.symptom_master[
            self.symptom_master["symptom_id"] == mapping_row["symptom_id"]
        ].iloc[0]

        # ---------------------------------------------
        # Basic symptom information
        # ---------------------------------------------

        symptom_id = master["symptom_id"]
        symptom_name = master["symptom_name"]
        onset_stage = mapping_row["onset_stage"]

        # ---------------------------------------------
        # Frequency
        # ---------------------------------------------

        frequency = mapping_row["frequency"]

        # ---------------------------------------------
        # Symptom severity
        #
        # We derive symptom severity from encounter
        # severity while allowing some variation.
        # ---------------------------------------------

        if encounter.severity_id == "SV001":
            symptom_severity = "Mild"

        elif encounter.severity_id == "SV002":
            symptom_severity = random.choice(
                ["Mild", "Moderate", "Moderate"]
            )

        else:
            symptom_severity = random.choice(
                ["Moderate", "Severe", "Severe"]
            )

        # ---------------------------------------------
        # Duration
        #
        # Symptoms occurring later in the illness tend
        # to have existed for at least part of the
        # encounter's onset period.
        # ---------------------------------------------

        onset_days = getattr(
            encounter,
            "symptom_onset_days",
            1
        )

        if onset_stage == "Early":
            minimum_duration = 1
        elif onset_stage == "Middle":
            minimum_duration = min(2, onset_days)
        else:
            minimum_duration = min(3, onset_days)

        minimum_duration = max(1, minimum_duration)

        duration_days = random.randint(
            minimum_duration,
            max(minimum_duration, onset_days)
        )

        # ---------------------------------------------
        # Progression
        # ---------------------------------------------

        progression_options = self.progression_by_severity.get(
            encounter.severity_id,
            ["Stable"]
        )

        progression = random.choice(progression_options)

        # ---------------------------------------------
        # Onset timestamp
        #
        # Encounter visit timestamp - symptom duration
        # ---------------------------------------------

        onset_timestamp = None

        if encounter.visit_timestamp is not None:
            onset_timestamp = (
                encounter.visit_timestamp
                - timedelta(days=duration_days)
            )

        return Symptom(

            symptom_id=symptom_id,

            symptom_name=symptom_name,

            onset_stage=onset_stage,

            severity=symptom_severity,

            duration_days=duration_days,

            frequency=frequency,

            progression=progression,

            onset_timestamp=onset_timestamp
        )

    # ======================================================
    # MAIN GENERATOR
    # ======================================================

    def generate(self, encounter):

        mappings = self.get_symptoms(
            encounter.disease_id
        )

        encounter.symptoms = []

        multiplier = self.severity_multiplier.get(
            encounter.severity_id,
            1.0
        )

        # ---------------------------------------------
        # Allowed onset stages based on severity
        # ---------------------------------------------

        if encounter.severity_id == "SV001":

            allowed_stages = ["Early"]

        elif encounter.severity_id == "SV002":

            allowed_stages = [
                "Early",
                "Middle"
            ]

        else:

            allowed_stages = [
                "Early",
                "Middle",
                "Late"
            ]

        # ---------------------------------------------
        # Generate Symptoms
        # ---------------------------------------------

        for _, row in mappings.iterrows():

            onset_stage = row["onset_stage"]

            # Skip symptoms that shouldn't appear yet

            if onset_stage not in allowed_stages:
                continue

            mandatory = row["mandatory"]
            frequency = row["frequency"]

            # -----------------------------------------
            # Mandatory symptoms
            # -----------------------------------------

            if mandatory:

                symptom = self.get_symptom(
                    row,
                    encounter
                )

                encounter.symptoms.append(symptom)

                continue

            # -----------------------------------------
            # Optional symptoms
            # -----------------------------------------

            probability = self.frequency_probability.get(
                frequency,
                0.50
            )

            probability *= multiplier

            probability = min(
                probability,
                1.0
            )

            if random.random() < probability:

                symptom = self.get_symptom(
                    row,
                    encounter
                )

                encounter.symptoms.append(symptom)

        return encounter