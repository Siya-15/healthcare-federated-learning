from sqlalchemy import text
from encounter_validator import EncounterValidator

class DatabaseWriter:

    def __init__(self, engine,validator=None):
        self.engine = engine
        self.validator = validator

    def save(self, encounter):
        if self.validator:
            self.validator.validate(encounter)

        """
        Writes one complete encounter into:

        - patient_encounter
        - encounter_symptoms
        - encounter_treatments
        - encounter_complications
        - encounter_labs
        - encounter_imaging

        Objective D:
        Persist the complete Encounter model without losing
        richer clinical attributes.
        """

        with self.engine.begin() as connection:

            # ==================================================
            # 1. PATIENT ENCOUNTER
            # ==================================================

            connection.execute(
                text("""
                    INSERT INTO patient_encounter (
                        encounter_id,
                        patient_id,
                        hospital_id,
                        parent_encounter_id,
                        visit_timestamp,
                        age,
                        gender,
                        occupation,
                        district,
                        state,
                        temperature,
                        heart_rate,
                        respiratory_rate,
                        systolic_bp,
                        diastolic_bp,
                        spo2,
                        disease_id,
                        severity_id,
                        admission_status,
                        visit_type,
                        symptom_onset_days,
                        travel_history,
                        vaccination_status,
                        discharge_status,
                        recovery_days,
                        treatment_duration_days,
                        readmitted_within_30_days,
                        follow_up_status,
                        complication_count,
                        admission_required,
                        referral_required
                    )
                    VALUES (
                        :encounter_id,
                        :patient_id,
                        :hospital_id,
                        :parent_encounter_id,
                        :visit_timestamp,
                        :age,
                        :gender,
                        :occupation,
                        :district,
                        :state,
                        :temperature,
                        :heart_rate,
                        :respiratory_rate,
                        :systolic_bp,
                        :diastolic_bp,
                        :spo2,
                        :disease_id,
                        :severity_id,
                        :admission_status,
                        :visit_type,
                        :symptom_onset_days,
                        :travel_history,
                        :vaccination_status,
                        :discharge_status,
                        :recovery_days,
                        :treatment_duration_days,
                        :readmitted_within_30_days,
                        :follow_up_status,
                        :complication_count,
                        :admission_required,
                        :referral_required
                    )
                """),
                {
                    "encounter_id": encounter.encounter_id,
                    "patient_id": encounter.patient_id,
                    "hospital_id": encounter.hospital_id,
                    "parent_encounter_id": encounter.parent_encounter_id,
                    "visit_timestamp": encounter.visit_timestamp,

                    "age": encounter.demographics.age,
                    "gender": encounter.demographics.gender,
                    "occupation": encounter.demographics.occupation,
                    "district": encounter.demographics.district,
                    "state": encounter.demographics.state,

                    "temperature": encounter.vitals.temperature,
                    "heart_rate": encounter.vitals.heart_rate,
                    "respiratory_rate": encounter.vitals.respiratory_rate,
                    "systolic_bp": encounter.vitals.systolic_bp,
                    "diastolic_bp": encounter.vitals.diastolic_bp,
                    "spo2": encounter.vitals.spo2,

                    "disease_id": encounter.disease_id,
                    "severity_id": encounter.severity_id,

                    "admission_status": (
                        "Admitted"
                        if encounter.admission_required
                        else "OPD"
                    ),

                    "visit_type": encounter.visit_type,

                    "symptom_onset_days": encounter.symptom_onset_days,

                    "travel_history": encounter.demographics.travel_history,

                    "vaccination_status": (
                        "Vaccinated"
                        if encounter.demographics.vaccination_status
                        else "Not Vaccinated"
                    ),

                    "discharge_status": {
                        "Recovered": "Recovered",
                        "Not Recovered": "Stable",
                        "Critical": "Referred"
                    }.get(encounter.outcome, "Stable"),

                    "recovery_days": encounter.recovery_days,

                    "treatment_duration_days":
                        encounter.treatment_duration_days,

                    "readmitted_within_30_days":
                        encounter.readmitted_within_30_days,

                    "follow_up_status":
                        encounter.follow_up_status,

                    "complication_count":
                        encounter.complication_count,

                    "admission_required":
                        encounter.admission_required,

                    "referral_required":
                        encounter.referral_required,
                }
            )

            # ==================================================
            # 2. SYMPTOMS
            # ==================================================

            for index, symptom in enumerate(encounter.symptoms):

                connection.execute(
                    text("""
                        INSERT INTO encounter_symptoms (
                            encounter_id,
                            symptom_id,
                            symptom_text,
                            symptom_source,
                            is_primary,
                            onset_stage,
                            severity,
                            duration_days,
                            frequency,
                            progression,
                            onset_timestamp
                        )
                        VALUES (
                            :encounter_id,
                            :symptom_id,
                            :symptom_text,
                            :symptom_source,
                            :is_primary,
                            :onset_stage,
                            :severity,
                            :duration_days,
                            :frequency,
                            :progression,
                            :onset_timestamp
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "symptom_id": symptom.symptom_id,
                        "symptom_text": symptom.symptom_name,
                        "symptom_source": "MASTER",
                        "is_primary": index == 0,

                        "onset_stage": {
                            "Early": "Initial",
                            "Middle": "Progressive",
                            "Late": "Severe"
                        }.get(
                            symptom.onset_stage,
                            symptom.onset_stage
                        ),

                        "severity": symptom.severity,
                        "duration_days": symptom.duration_days,
                        "frequency": symptom.frequency,
                        "progression": symptom.progression,
                        "onset_timestamp": symptom.onset_timestamp,
                    }
                )

            # ==================================================
            # 3. TREATMENTS
            # ==================================================

            for index, treatment in enumerate(encounter.treatments):

                connection.execute(
                    text("""
                        INSERT INTO encounter_treatments (
                            encounter_id,
                            treatment_id,
                            treatment_sequence,
                            dose,
                            dose_unit,
                            frequency,
                            duration_days,
                            start_timestamp,
                            end_timestamp,
                            adverse_effect,
                            recommended_by_ai,
                            administered,
                            treatment_notes,
                            accepted_by_doctor,
                            treatment_origin
                        )
                        VALUES (
                            :encounter_id,
                            :treatment_id,
                            :treatment_sequence,
                            :dose,
                            :dose_unit,
                            :frequency,
                            :duration_days,
                            :start_timestamp,
                            :end_timestamp,
                            :adverse_effect,
                            :recommended_by_ai,
                            :administered,
                            :treatment_notes,
                            :accepted_by_doctor,
                            :treatment_origin
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "treatment_id": treatment.treatment_id,
                        "treatment_sequence": index + 1,

                        "dose": treatment.dose,
                        "dose_unit": treatment.dose_unit,
                        "frequency": treatment.frequency,
                        "duration_days": treatment.duration_days,
                        "start_timestamp": treatment.start_timestamp,
                        "end_timestamp": treatment.end_timestamp,
                        "adverse_effect": treatment.adverse_effect,

                        # Historical/generated treatment.
                        # Not an AI recommendation.
                        "recommended_by_ai": False,
                        "administered": True,
                        "treatment_notes": None,
                        "accepted_by_doctor": True,
                        "treatment_origin": "Doctor",
                    }
                )

            # ==================================================
            # 4. COMPLICATIONS
            # ==================================================

            for complication in encounter.complications:

                connection.execute(
                    text("""
                        INSERT INTO encounter_complications (
                            encounter_id,
                            complication_id,
                            identified_timestamp,
                            resolved,
                            severity_id,
                            resolution_timestamp,
                            notes
                        )
                        VALUES (
                            :encounter_id,
                            :complication_id,
                            :identified_timestamp,
                            :resolved,
                            :severity_id,
                            :resolution_timestamp,
                            :notes
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "complication_id": complication.complication_id,

                        "identified_timestamp":
                            complication.identified_timestamp,
                            

                        "resolved": complication.resolved,

                        "severity_id":
                            complication.severity_id,

                        "resolution_timestamp":
                            complication.resolution_timestamp,

                        "notes":
                            complication.notes,
                    }
                )

            # ==================================================
            # 5. LAB RESULTS
            # ==================================================

            for lab in encounter.labs:

                connection.execute(
                    text("""
                        INSERT INTO encounter_labs (
                            encounter_id,
                            test_code,
                            test_name,
                            result_value,
                            unit,
                            reference_range_low,
                            reference_range_high,
                            abnormal_flag,
                            test_timestamp
                        )
                        VALUES (
                            :encounter_id,
                            :test_code,
                            :test_name,
                            :result_value,
                            :unit,
                            :reference_range_low,
                            :reference_range_high,
                            :abnormal_flag,
                            :test_timestamp
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "test_code": lab.test_code,
                        "test_name": lab.test_name,
                        "result_value": lab.result_value,
                        "unit": lab.unit,
                        "reference_range_low": lab.reference_range_low,
                        "reference_range_high": lab.reference_range_high,

                        # PostgreSQL currently stores this as VARCHAR(20)
                        "abnormal_flag": (
                            str(lab.abnormal_flag)
                            if lab.abnormal_flag is not None
                            else None
                        ),

                        "test_timestamp": lab.test_timestamp,
                    }
                )

            # ==================================================
            # 6. IMAGING RESULTS
            # ==================================================

            for imaging in encounter.imaging:

                connection.execute(
                    text("""
                        INSERT INTO encounter_imaging (
                            encounter_id,
                            imaging_id,
                            imaging_name,
                            modality,
                            body_site,
                            finding,
                            impression,
                            performed_timestamp
                        )
                        VALUES (
                            :encounter_id,
                            :imaging_id,
                            :imaging_name,
                            :modality,
                            :body_site,
                            :finding,
                            :impression,
                            :performed_timestamp
                        )
                    """),
                    {
                        "encounter_id": encounter.encounter_id,
                        "imaging_id": imaging.imaging_id,
                        "imaging_name": imaging.imaging_name,
                        "modality": imaging.modality,
                        "body_site": imaging.body_site,
                        "finding": imaging.finding,
                        "impression": imaging.impression,
                        "performed_timestamp":
                            imaging.performed_timestamp,
                    }
                )