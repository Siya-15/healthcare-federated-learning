from models.encounter import Encounter


class SimulationEngine:

    def __init__(

        self,

        daily_generator,

        encounter_generator,

        demographics_generator,

        disease_generator,

        severity_generator,

        symptom_generator,
        symptom_onset_generator,

        vitals_generator,

        treatment_generator,

        complication_generator,

        outcome_generator

    ):

        self.daily_generator = daily_generator

        self.encounter_generator = encounter_generator

        self.demographics_generator = demographics_generator

        self.disease_generator = disease_generator

        self.severity_generator = severity_generator

        self.symptom_generator = symptom_generator
        self.symptom_onset_generator = symptom_onset_generator

        self.vitals_generator = vitals_generator

        self.treatment_generator = treatment_generator

        self.complication_generator = complication_generator

        self.outcome_generator = outcome_generator

    # =====================================================

    def generate_patient(self, context):

        encounter = Encounter()
        
        encounter.hospital_id = context.hospital_id

        self.encounter_generator.generate(encounter, context)

        self.demographics_generator.generate(encounter)

        self.disease_generator.generate(encounter, context)

        self.severity_generator.generate(encounter)

        self.symptom_generator.generate(encounter)
        self.symptom_onset_generator.generate(encounter)

        self.vitals_generator.generate(encounter)

        self.treatment_generator.generate(encounter)

        self.complication_generator.generate(encounter)

        self.outcome_generator.generate(encounter)

        return encounter