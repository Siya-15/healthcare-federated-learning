from flwr.app import (
    Context,
    ArrayRecord,
)

from flwr.serverapp import ServerApp
from flwr.serverapp.strategy import FedAvg

from .model_utils import (
    initialize_model,
    get_model_parameters,
)


# ==========================================================
# FLOWER SERVER
# ==========================================================

app = ServerApp()



# ==========================================================
# SERVER
# ==========================================================

@app.main()
def main(
    grid,
    context: Context,
):

    print("=" * 70)
    print("FEDERATED LEARNING SERVER")
    print("=" * 70)

    print(
        "\nFederated task:"
        " Multi-label symptom prediction"
    )

    print(
        "Hospitals:"
        " 10"
    )

    print(
        "Raw patient data:"
        " LOCAL ONLY"
    )

    # ------------------------------------------------------
    # INITIAL GLOBAL MODEL
    # ------------------------------------------------------

    model = initialize_model()

    initial_parameters = (
        get_model_parameters(model)
    )

    initial_arrays = ArrayRecord(
        initial_parameters
    )

    # ------------------------------------------------------
    # FEDAVG
    # ------------------------------------------------------

    strategy = FedAvg(
        fraction_train=1.0,
        fraction_evaluate=1.0,

        min_train_nodes=10,
        min_evaluate_nodes=10,
        min_available_nodes=10,

        
    )

    print(
        "\nStarting federated learning "
        "across 10 hospitals..."
    )

    # ------------------------------------------------------
    # FEDERATED TRAINING
    # ------------------------------------------------------

    result = strategy.start(
        grid=grid,
        initial_arrays=initial_arrays,
        num_rounds=3,
    )

    print(
        "\nFederated learning completed."
    )

    print(
        "Global multi-label model "
        "successfully aggregated."
    )