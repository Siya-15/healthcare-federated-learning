def print_encounter(encounter, tables, context=None):

    print(f"Hospital ID     : {encounter.hospital_id}")

    print("\n" + "=" * 80)
    print(f"PATIENT ID      : {encounter.encounter_id}")
    print("=" * 80)

    # =====================================================
    # GENERAL INFORMATION
    # =====================================================

    print("\nGENERAL INFORMATION")
    print("-" * 40)

    if context is not None:
        print(f"Hospital        : {context.hospital_id}")

    print(f"Visit Time      : {encounter.visit_timestamp}")

    # =====================================================
    # DEMOGRAPHICS
    # =====================================================

    print("\nDEMOGRAPHICS")
    print("-" * 40)

    print(f"Age             : {encounter.demographics.age}")
    print(f"Gender          : {encounter.demographics.gender}")
    print(f"Occupation      : {encounter.demographics.occupation}")
    print(f"Vaccinated      : {encounter.demographics.vaccination_status}")
    print(f"Travel History  : {encounter.demographics.travel_history}")

    # =====================================================
    # DIAGNOSIS
    # =====================================================

    disease_name = tables["disease_master"].loc[
        tables["disease_master"]["disease_id"] == encounter.disease_id,
        "disease_name"
    ].iloc[0]

    severity_name = tables["severity_master"].loc[
        tables["severity_master"]["severity_id"] == encounter.severity_id,
        "severity_name"
    ].iloc[0]

    print("\nDIAGNOSIS")
    print("-" * 40)

    print(f"Disease         : {disease_name} ({encounter.disease_id})")
    print(f"Severity        : {severity_name} ({encounter.severity_id})")

    # =====================================================
    # SYMPTOMS
    # =====================================================

    print("\nSYMPTOMS")
    print("-" * 40)

    if encounter.symptoms:

        for symptom in encounter.symptoms:

            print(
                f"• {symptom.symptom_name:<25}"
                f"{symptom.onset_stage}"
            )

    else:

        print("None")

    # =====================================================
    # VITALS
    # =====================================================

    print("\nVITALS")
    print("-" * 40)

    print(f"Temperature     : {encounter.vitals.temperature} °C")
    print(f"Heart Rate      : {encounter.vitals.heart_rate} bpm")
    print(f"SpO₂            : {encounter.vitals.spo2} %")

    print(
        f"Blood Pressure  : "
        f"{encounter.vitals.systolic_bp}/"
        f"{encounter.vitals.diastolic_bp} mmHg"
    )

    # =====================================================
    # TREATMENTS
    # =====================================================

    print("\nTREATMENTS")
    print("-" * 40)

    if encounter.treatments:

        for treatment in encounter.treatments:

            print(f"• {treatment.treatment_name}")

    else:

        print("None")

    # =====================================================
    # COMPLICATIONS
    # =====================================================

    print("\nCOMPLICATIONS")
    print("-" * 40)

    if encounter.complications:

        for complication in encounter.complications:

            print(f"• {complication.complication_name}")

    else:

        print("None")

    # =====================================================
    # OUTCOME
    # =====================================================

    print("\nOUTCOME")
    print("-" * 40)

    print(f"Outcome         : {encounter.outcome}")
    print(f"Recovery Days   : {encounter.recovery_days}")

    if hasattr(encounter, "admission_required"):
        print(f"Admission       : {encounter.admission_required}")

    if hasattr(encounter, "referral_required"):
        print(f"Referral        : {encounter.referral_required}")

    print("=" * 80)