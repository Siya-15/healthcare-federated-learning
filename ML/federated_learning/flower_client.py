from flwr.app import (
    Context,
    Message,
    ArrayRecord,
    MetricRecord,
    RecordDict,
)

from sklearn.metrics import (
    f1_score,
    hamming_loss,
    accuracy_score,
)

from flwr.clientapp import ClientApp

from .task import load_data

from .model_utils import (
    initialize_model,
    get_model_parameters,
)


# ==========================================================
# FLOWER CLIENT
# ==========================================================

app = ClientApp()


# ==========================================================
# HOSPITAL MAPPING
# ==========================================================

def get_hospital_id(context):

    hospital_ids = [
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

    node_id = int(context.node_id)

    return hospital_ids[
        node_id % len(hospital_ids)
    ]


# ==========================================================
# LOAD GLOBAL PARAMETERS
# ==========================================================

def set_model_parameters(
    model,
    parameters
):

    state_dict = model.network.state_dict()

    new_state_dict = {}

    for (
        (key, old_value),
        new_value,
    ) in zip(
        state_dict.items(),
        parameters,
    ):

        new_state_dict[key] = (
            old_value.new_tensor(
                new_value
            )
        )

    model.network.load_state_dict(
        new_state_dict
    )


# ==========================================================
# TRAIN
# ==========================================================

@app.train()
def train(
    msg: Message,
    context: Context,
):

    hospital_id = get_hospital_id(
        context
    )

    print(
        f"\n[{hospital_id}] "
        "Received global model."
    )

    # ------------------------------------------------------
    # LOCAL DATA
    # ------------------------------------------------------

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = load_data(
        hospital_id
    )

    print(
        f"[{hospital_id}] "
        f"Local records: "
        f"{len(X_train)}"
    )

    print(
        f"[{hospital_id}] "
        f"Local symptom labels: "
        f"{y_train.shape[1]}"
    )

    # ------------------------------------------------------
    # CREATE MODEL
    # ------------------------------------------------------

    model = initialize_model()

    # ------------------------------------------------------
    # RECEIVE GLOBAL MODEL
    # ------------------------------------------------------

    global_parameters = (
        msg.content["arrays"]
        .to_numpy_ndarrays()
    )

    set_model_parameters(
        model,
        global_parameters
    )

    # ------------------------------------------------------
    # LOCAL TRAINING
    # ------------------------------------------------------

    print(
        f"[{hospital_id}] "
        "Training local model..."
    )

    model.fit(
        X_train,
        y_train,
        max_epochs=5,
        batch_size=128,
    )

    print(
        f"[{hospital_id}] "
        "Local training completed."
    )

    # ------------------------------------------------------
    # GET UPDATED PARAMETERS
    # ------------------------------------------------------

    updated_parameters = (
        get_model_parameters(model)
    )

    # ------------------------------------------------------
    # SEND ONLY MODEL UPDATE
    # ------------------------------------------------------

    content = RecordDict({

        "arrays": ArrayRecord(
            updated_parameters
        ),

        "metrics": MetricRecord({

            "num-examples":
                len(X_train),

        }),

    })

    return Message(
        content=content,
        reply_to=msg,
    )


# ==========================================================
# EVALUATE
# ==========================================================

@app.evaluate()
def evaluate(
    msg: Message,
    context: Context,
):

    hospital_id = get_hospital_id(
        context
    )

    print(
        f"\n[{hospital_id}] "
        "Evaluating global model..."
    )

    # ------------------------------------------------------
    # LOCAL TEST DATA
    # ------------------------------------------------------

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = load_data(
        hospital_id
    )

    # ------------------------------------------------------
    # CREATE MODEL
    # ------------------------------------------------------

    model = initialize_model()

    # ------------------------------------------------------
    # LOAD GLOBAL PARAMETERS
    # ------------------------------------------------------

    global_parameters = (
        msg.content["arrays"]
        .to_numpy_ndarrays()
    )

    set_model_parameters(
        model,
        global_parameters
    )

    # ------------------------------------------------------
    # GLOBAL MODEL PREDICTIONS
    # ------------------------------------------------------

    predictions = model.predict(
        X_test
    )

    # ------------------------------------------------------
    # MULTI-LABEL METRICS
    # ------------------------------------------------------

    # 1. Element-wise accuracy
    element_accuracy = (
        predictions == y_test
    ).mean()

    # 2. Exact-match accuracy
    #
    # A patient counts as correct only if
    # ALL 27 symptom labels are correct.
    exact_match_accuracy = accuracy_score(
        y_test,
        predictions
    )

    # 3. Hamming loss
    #
    # Lower is better.
    hamming = hamming_loss(
        y_test,
        predictions
    )

    # 4. Micro F1
    micro_f1 = f1_score(
        y_test,
        predictions,
        average="micro",
        zero_division=0
    )

    # 5. Macro F1
    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0
    )

    # ------------------------------------------------------
    # PRINT RESULTS
    # ------------------------------------------------------

    print(
        f"[{hospital_id}] "
        f"Element accuracy: "
        f"{element_accuracy:.4f}"
    )

    print(
        f"[{hospital_id}] "
        f"Exact-match accuracy: "
        f"{exact_match_accuracy:.4f}"
    )

    print(
        f"[{hospital_id}] "
        f"Hamming loss: "
        f"{hamming:.4f}"
    )

    print(
        f"[{hospital_id}] "
        f"Micro F1: "
        f"{micro_f1:.4f}"
    )

    print(
        f"[{hospital_id}] "
        f"Macro F1: "
        f"{macro_f1:.4f}"
    )

    # ------------------------------------------------------
    # SEND METRICS TO SERVER
    # ------------------------------------------------------

    content = RecordDict({

        "metrics": MetricRecord({

            "element_accuracy":
                float(element_accuracy),

            "exact_match_accuracy":
                float(exact_match_accuracy),

            "hamming_loss":
                float(hamming),

            "micro_f1":
                float(micro_f1),

            "macro_f1":
                float(macro_f1),

            "num-examples":
                len(X_test),

        }),

    })

    return Message(
        content=content,
        reply_to=msg,
    )