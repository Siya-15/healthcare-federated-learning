import random

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

    # ======================================================
    # GET SYMPTOMS
    # ======================================================

    def get_symptoms(self, disease_id):

        return self.symptom_mapping[
            self.symptom_mapping["disease_id"] == disease_id
        ]

    # ======================================================
    # GET SYMPTOM NAME
    # ======================================================

    def get_symptom(self, mapping_row):

        master = self.symptom_master[
            self.symptom_master["symptom_id"] == mapping_row["symptom_id"]
        ].iloc[0]

        return Symptom(

            symptom_id=master["symptom_id"],

            symptom_name=master["symptom_name"],

            onset_stage=mapping_row["onset_stage"]

        )

    # ======================================================
    # MAIN GENERATOR
    # ======================================================

    def generate(self, encounter):

        mappings = self.get_symptoms(encounter.disease_id)

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

            symptom = self.get_symptom(row)

            mandatory = row["mandatory"]

            frequency = row["frequency"]


            # ---------------------------------------------
            # Mandatory symptoms
            # ---------------------------------------------

            if mandatory:

                encounter.symptoms.append(symptom)

                continue

            # ---------------------------------------------
            # Optional symptoms
            # ---------------------------------------------

            probability = self.frequency_probability.get(
                frequency,
                0.50
            )

            probability *= multiplier

            probability = min(probability, 1.0)

            if random.random() < probability:

                encounter.symptoms.append(symptom)

        return encounter