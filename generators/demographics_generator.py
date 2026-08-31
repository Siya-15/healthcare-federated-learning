import random


class DemographicsGenerator:

    def __init__(self, tables):

        self.hospital_master = tables["hospital_master"]

        # --------------------------------------------------
        # Gender Distribution
        # --------------------------------------------------

        self.gender_distribution = {
            "Male": 0.51,
            "Female": 0.49
        }

        # --------------------------------------------------
        # Age Group Distribution
        # --------------------------------------------------

        self.child_probability = 0.20
        self.adult_probability = 0.65
        self.elderly_probability = 0.15

        # --------------------------------------------------
        # Probabilities
        # --------------------------------------------------

        self.travel_probability = 0.25
        self.vaccination_probability = 0.80

        # --------------------------------------------------
        # Occupations
        # --------------------------------------------------

        self.child_occupations = [
            "Student"
        ]

        self.adult_occupations = [

            "Software Engineer",
            "Teacher",
            "Doctor",
            "Nurse",
            "Farmer",
            "Business Owner",
            "Driver",
            "Factory Worker",
            "Office Worker",
            "Government Employee",
            "Police Officer",
            "Sales Executive",
            "Electrician",
            "Mechanic",
            "Shopkeeper",
            "Lab Technician",
            "Pharmacist",
            "Homemaker"

        ]

        self.elderly_occupations = [

            "Retired",
            "Retired Teacher",
            "Retired Government Employee",
            "Retired Army Officer",
            "Retired Farmer",
            "Homemaker"

        ]

    # ======================================================
    # AGE
    # ======================================================

    def generate_age(self):

        r = random.random()

        if r < self.child_probability:

            return random.randint(1, 17)

        elif r < self.child_probability + self.adult_probability:

            return random.randint(18, 60)

        else:

            return random.randint(61, 90)

    # ======================================================
    # GENDER
    # ======================================================

    def generate_gender(self):

        r = random.random()

        cumulative = 0

        for gender, probability in self.gender_distribution.items():

            cumulative += probability

            if r <= cumulative:

                return gender

        return "Male"

    # ======================================================
    # OCCUPATION
    # ======================================================

    def generate_occupation(self, age):

        if age < 18:

            return random.choice(self.child_occupations)

        elif age < 60:

            return random.choice(self.adult_occupations)

        else:

            return random.choice(self.elderly_occupations)

    # ======================================================
    # TRAVEL HISTORY
    # ======================================================

    def generate_travel_history(self):

        return random.random() < self.travel_probability

    # ======================================================
    # VACCINATION STATUS
    # ======================================================

    def generate_vaccination_status(self):

        return random.random() < self.vaccination_probability

    # ======================================================
    # LOCATION
    # ======================================================

    def generate_location(self, hospital_id):

        hospital = self.hospital_master[
            self.hospital_master["hospital_id"] == hospital_id
        ].iloc[0]

        return hospital["city"], hospital["state"]

    # ======================================================
    # MAIN FUNCTION
    # ======================================================

    def generate(self, encounter):

        age = self.generate_age()

        encounter.demographics.age = age

        encounter.demographics.gender = self.generate_gender()

        encounter.demographics.occupation = self.generate_occupation(age)

        encounter.demographics.travel_history = self.generate_travel_history()

        encounter.demographics.vaccination_status = (
            self.generate_vaccination_status()
        )

        city, state = self.generate_location(
            encounter.hospital_id
        )

        encounter.demographics.district = city
        encounter.demographics.state = state

        return encounter