import random


class SeverityGenerator:

    def __init__(self, tables):

        self.config = tables["disease_generation_config"]

    # ======================================================
    # GET CONFIG FOR DISEASE
    # ======================================================

    def get_config(self, disease_id):

        row = self.config[
            self.config["disease_id"] == disease_id
        ].iloc[0]

        return row

    # ======================================================
    # GENERATE SEVERITY
    # ======================================================

    def generate(self, encounter):

        config = self.get_config(encounter.disease_id)

        severities = [
            "SV001",
            "SV002",
            "SV003"
        ]

        weights = [

            config["mild_percentage"],

            config["moderate_percentage"],

            config["severe_percentage"]

        ]

        severity = random.choices(

            population=severities,

            weights=weights,

            k=1

        )[0]

        encounter.severity_id = severity

        return encounter