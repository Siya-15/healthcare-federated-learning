import random


class SymptomOnsetGenerator:

    def generate(self, encounter):

        if encounter.severity_id == "SV001":
            # Mild cases usually present relatively early
            days = random.randint(1, 4)

        elif encounter.severity_id == "SV002":
            # Moderate cases may present after several days
            days = random.randint(2, 7)

        else:
            # Severe cases may present later in the illness
            days = random.randint(4, 10)

        encounter.symptom_onset_days = days

        return encounter