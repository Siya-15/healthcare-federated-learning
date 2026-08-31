import random

from models.encounter import Complication


class ComplicationGenerator:

    def __init__(self, tables):

        self.mapping = tables["disease_complication_mapping"]

        self.master = tables["complication_master"]

        self.frequency_probability = {

            "Rare": 0.15,

            "Occasional": 0.35,

            "Common": 0.60,

            "Very Common": 0.85

        }

    # =====================================================
    # GET COMPLICATIONS
    # =====================================================

    def get_complications(self, disease_id):

        return self.mapping[

            self.mapping["disease_id"] == disease_id

        ]

    # =====================================================
    # GET COMPLICATION DETAILS
    # =====================================================

    def get_complication(self, complication_id):

        row = self.master[
            self.master["complication_id"] == complication_id
        ].iloc[0]

        return Complication(

            complication_id=row["complication_id"],

            complication_name=row["complication_name"]

        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(self, encounter):

        mappings = self.get_complications(

            encounter.disease_id

        )

        encounter.complications = []

        for _, row in mappings.iterrows():

            # Ignore complications more severe than the patient
            if row["severity_id"] != encounter.severity_id:
                continue

            probability = self.frequency_probability.get(

                row["frequency"],

                0.30

            )

            if random.random() < probability:

                complication = self.get_complication(

                    row["complication_id"]

                )

                encounter.complications.append(

                    complication

                )

        return encounter