from ML.federated_learning.task import load_data


HOSPITALS = [
    "H001",
    "H002",
    "H003",
    "H004",
    "H005",
    "H006",
    "H007",
    "H008",
    "H009",
    "H010",
]


def main():

    print("=" * 70)
    print("C3 REAL HOSPITAL STANDARDIZATION VALIDATION")
    print("=" * 70)

    reference_X_shape = None
    reference_y_shape = None

    all_passed = True

    for hospital_id in HOSPITALS:

        try:

            X_train, X_test, y_train, y_test = (
                load_data(hospital_id)
            )

            print(
                f"\n{hospital_id}"
            )

            print(
                f"  X_train: {X_train.shape}"
            )

            print(
                f"  X_test : {X_test.shape}"
            )

            print(
                f"  y_train: {y_train.shape}"
            )

            print(
                f"  y_test : {y_test.shape}"
            )

            if X_train.shape[1] != 10:
                raise ValueError(
                    "Expected 10 features."
                )

            if y_train.shape[1] != 27:
                raise ValueError(
                    "Expected 27 targets."
                )

            if reference_X_shape is None:

                reference_X_shape = (
                    X_train.shape[1]
                )

                reference_y_shape = (
                    y_train.shape[1]
                )

            if (
                X_train.shape[1]
                != reference_X_shape
            ):
                raise ValueError(
                    "Feature dimensions differ."
                )

            if (
                y_train.shape[1]
                != reference_y_shape
            ):
                raise ValueError(
                    "Target dimensions differ."
                )

            print(
                "  STATUS: PASS"
            )

        except Exception as error:

            all_passed = False

            print(
                f"  STATUS: FAIL - {error}"
            )

    print("\n" + "=" * 70)

    if all_passed:

        print(
            "C3 VALIDATION: PASS"
        )

    else:

        print(
            "C3 VALIDATION: FAIL"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()