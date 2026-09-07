import random


class DiseaseGenerator:

    def __init__(self, tables):

        self.disease_master = tables["disease_master"]
        self.config = tables["disease_generation_config"]

        # --------------------------------------------------
        # HOSPITAL-SPECIFIC DISEASE MULTIPLIERS
        # --------------------------------------------------

        # These create controlled non-IID distributions
        # across hospitals for federated learning simulation.

        self.hospital_rules = {

            "H001": {       # AIIMS New Delhi
                "D004": 1.20,
                "D005": 1.15,
                "D001": 0.90
            },

            "H002": {       # PGIMER Chandigarh
                "D004": 1.15,
                "D005": 1.10,
                "D002": 0.90
            },

            "H003": {       # JIPMER Puducherry
                "D001": 1.20,
                "D002": 1.15,
                "D003": 1.20,
                "D004": 0.90
            },

            "H004": {       # CMC Vellore
                "D005": 1.15,
                "D008": 1.10,
                "D004": 1.05
            },

            "H005": {       # KGMU Lucknow
                "D007": 1.20,
                "D008": 1.15,
                "D003": 0.90
            },

            "H006": {       # NIMHANS Bengaluru
                "D006": 1.40,
                "D005": 1.10,
                "D004": 0.90
            },

            "H007": {       # Safdarjung Hospital
                "D004": 1.15,
                "D005": 1.10,
                "D001": 0.90
            },

            "H008": {       # KEM Mumbai
                "D005": 1.20,
                "D001": 1.05,
                "D004": 0.95
            },

            "H009": {       # Sree Chitra Tirunal
                "D002": 1.15,
                "D003": 1.15,
                "D008": 1.10,
                "D004": 0.90
            },

            "H010": {       # SMS Medical College Jaipur
                "D007": 1.15,
                "D008": 1.15,
                "D005": 0.90
            }

        }

        # --------------------------------------------------
        # AGE MULTIPLIERS
        # --------------------------------------------------

        self.age_rules = {

            "child": {
                "D004": 1.30,     # Influenza
                "D008": 1.20      # Gastroenteritis
            },

            "adult": {
                # No modification
            },

            "elderly": {
                "D004": 1.50,     # Influenza
                "D005": 1.40,     # COVID
                "D006": 1.20      # Tuberculosis
            }

        }

        # --------------------------------------------------
        # SEASON MULTIPLIERS
        # --------------------------------------------------

        self.season_rules = {

            "Summer": {
                "D008": 1.30
            },

            "Monsoon": {
                "D001": 1.80,     # Dengue
                "D002": 1.60,     # Malaria
                "D003": 1.50      # Chikungunya
            },

            "Winter": {
                "D004": 1.70,     # Influenza
                "D005": 1.30      # COVID
            }

        }

    # ======================================================
    # AGE GROUP
    # ======================================================

    def get_age_group(self, age):

        if age < 18:
            return "child"

        elif age < 60:
            return "adult"

        return "elderly"

    # ======================================================
    # APPLY HOSPITAL RULES
    # ======================================================

    def apply_hospital_rules(self, weights, context):

        hospital_id = context.hospital_id

        if hospital_id not in self.hospital_rules:
            return

        for disease, multiplier in self.hospital_rules[hospital_id].items():

            if disease in weights:

                weights[disease] *= multiplier

    # ======================================================
    # APPLY AGE RULES
    # ======================================================

    def apply_age_rules(self, weights, encounter):

        age_group = self.get_age_group(
            encounter.demographics.age
        )

        if age_group not in self.age_rules:
            return

        for disease, multiplier in self.age_rules[age_group].items():

            if disease in weights:

                weights[disease] *= multiplier

    # ======================================================
    # APPLY SEASON RULES
    # ======================================================

    def apply_season_rules(self, weights, context):

        season = context.season

        if season not in self.season_rules:
            return

        for disease, multiplier in self.season_rules[season].items():

            if disease in weights:

                weights[disease] *= multiplier

    # ======================================================
    # APPLY OUTBREAK
    # ======================================================

    def apply_outbreak_rules(self, weights, context):

        if not context.outbreak_active:
            return

        disease = context.outbreak_disease

        if disease in weights:

            weights[disease] *= 3.0

    # ======================================================
    # GENERATE
    # ======================================================

    def generate(self, encounter, context):

        weights = {}

        for _, row in self.config.iterrows():

            weights[row["disease_id"]] = row["prevalence_weight"]

        

        # ----------------------------------------------
        # APPLY HOSPITAL-SPECIFIC DISTRIBUTION
        # ----------------------------------------------

        self.apply_hospital_rules(weights, context)

        # ----------------------------------------------
        # APPLY DEMOGRAPHIC EFFECTS
        # ----------------------------------------------

        self.apply_age_rules(weights, encounter)

        # ----------------------------------------------
        # APPLY SEASONAL EFFECTS
        # ----------------------------------------------

        self.apply_season_rules(weights, context)

        # ----------------------------------------------
        # APPLY OUTBREAK EFFECTS
        # ----------------------------------------------

        self.apply_outbreak_rules(weights, context)

        # ----------------------------------------------

        diseases = list(weights.keys())

        probabilities = list(weights.values())

        selected = random.choices(

            population=diseases,

            weights=probabilities,

            k=1

        )[0]

        encounter.disease_id = selected

        return encounter