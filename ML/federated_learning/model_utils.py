import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from .task import TARGET_COLUMNS


# ==========================================================
# MULTI-LABEL NEURAL NETWORK
# ==========================================================

class MultiLabelNet(nn.Module):

    def __init__(self, input_dim=10, output_dim=27):

        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),

            nn.Linear(32, 32),
            nn.ReLU(),

            nn.Linear(32, output_dim),
        )

    def forward(self, x):

        return self.network(x)


# ==========================================================
# MODEL WRAPPER
# ==========================================================

class MultiLabelModel:

    def __init__(self):

        self.network = MultiLabelNet(
            input_dim=10,
            output_dim=len(TARGET_COLUMNS),
        )

    # ------------------------------------------------------
    # TRAIN
    # ------------------------------------------------------

    def fit(
        self,
        X,
        y,
        max_epochs=5,
        batch_size=128,
        **kwargs
    ):

        X_tensor = torch.tensor(
            X,
            dtype=torch.float32
        )

        y_tensor = torch.tensor(
            y,
            dtype=torch.float32
        )

        dataset = torch.utils.data.TensorDataset(
            X_tensor,
            y_tensor
        )

        loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True
        )

        optimizer = optim.Adam(
            self.network.parameters(),
            lr=0.001
        )

        criterion = nn.BCEWithLogitsLoss()

        self.network.train()

        for epoch in range(max_epochs):

            total_loss = 0.0

            for batch_X, batch_y in loader:

                optimizer.zero_grad()

                logits = self.network(
                    batch_X
                )

                loss = criterion(
                    logits,
                    batch_y
                )

                loss.backward()

                optimizer.step()

                total_loss += loss.item()

    # ------------------------------------------------------
    # PREDICT
    # ------------------------------------------------------

    def predict_proba(self, X):

        self.network.eval()

        X_tensor = torch.tensor(
            X,
            dtype=torch.float32
        )

        with torch.no_grad():

            logits = self.network(
                X_tensor
            )

            probabilities = torch.sigmoid(
                logits
            )

        return probabilities.numpy()

    # ------------------------------------------------------
    # PREDICT LABELS
    # ------------------------------------------------------

    def predict(self, X):

        probabilities = self.predict_proba(X)

        return (
            probabilities >= 0.5
        ).astype(int)


# ==========================================================
# INITIALIZE MODEL
# ==========================================================

def initialize_model():

    return MultiLabelModel()


# ==========================================================
# GET MODEL PARAMETERS
# ==========================================================

def get_model_parameters(model):

    return [
        value.detach()
        .cpu()
        .numpy()
        for value in model.network.state_dict().values()
    ]