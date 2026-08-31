from models.encounter import Treatment


class TreatmentGenerator:

    def __init__(self, tables):

        self.mapping = tables["disease_treatment_mapping"]

        self.master = tables["treatment_master"]

    # =====================================================
    # GET TREATMENTS
    # =====================================================

    def get_treatments(self, disease_id, severity_id):

        return self.mapping[

            (self.mapping["disease_id"] == disease_id) &

            (self.mapping["severity_id"] == severity_id)

        ]

    # =====================================================
    # GET TREATMENT DETAILS
    # =====================================================

    def get_treatment(self, treatment_id):

        row = self.master[
            self.master["treatment_id"] == treatment_id
        ].iloc[0]

        return Treatment(

            treatment_id=row["treatment_id"],

            treatment_name=row["treatment_name"]

        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(self, encounter):

        mappings = self.get_treatments(

            encounter.disease_id,

            encounter.severity_id

        )

        encounter.treatments = []

        for _, row in mappings.iterrows():

            treatment = self.get_treatment(

                row["treatment_id"]

            )

            encounter.treatments.append(

                treatment

            )

        return encounter