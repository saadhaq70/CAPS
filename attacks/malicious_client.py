"""
ASH-FL Phase 2: MaliciousClient
Extends HeartDiseaseClient to apply a configured attack inside fit().
The evaluate() method is inherited unchanged so server-side metrics
reflect the global model on clean data (no cheating the evaluation).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from clients.client import (
    HeartDiseaseClient,
    get_model_parameters,
    set_model_parameters,
    train_model,
)
from attacks.base import AttackConfig, BaseAttack


class MaliciousClient(HeartDiseaseClient):
    """
    A drop-in replacement for HeartDiseaseClient that injects an attack.

    Behaviour per round inside ``fit()``:
      1. Receive global parameters from the server (same as benign client).
      2. Call ``attack.poison_data()`` on the local training set.
      3. Run local SGD on the (possibly poisoned) data.
      4. Call ``attack.poison_update()`` on the resulting parameters.
      5. Return the (possibly modified) parameters to the server.

    The ``evaluate()`` method is NOT overridden; malicious clients still
    report honest evaluation metrics so the attack remains stealthy.

    Attributes:
        is_malicious: Always True — used by Phase 3+ for ground-truth scoring.
        attack: Concrete BaseAttack instance performing the poisoning.
    """

    #: Ground-truth flag; benign HeartDiseaseClient does not have this.
    is_malicious: bool = True

    def __init__(
        self,
        cid: int,
        X_train: np.ndarray,
        y_train: np.ndarray,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        batch_size: int,
        learning_rate: float,
        local_epochs: int,
        attack: BaseAttack,
    ) -> None:
        """
        Initialize malicious client.

        Args:
            cid:           Client ID.
            X_train:       Raw (pre-poison) training features.
            y_train:       Raw (pre-poison) training labels.
            input_dim:     Input feature dimension.
            hidden_dim:    Hidden layer size.
            output_dim:    Output dimension (1 for binary).
            batch_size:    Mini-batch size for local SGD.
            learning_rate: SGD learning rate.
            local_epochs:  Number of local training epochs per round.
            attack:        Instantiated attack object (from ``get_attack()``).
        """
        # Store raw data before poisoning (super().__init__ builds the loader)
        self._X_raw = X_train.copy()
        self._y_raw = y_train.copy()
        self._attack = attack

        # Parent init builds self.train_loader from the raw data — we will
        # rebuild a poisoned loader inside fit() each round.
        super().__init__(
            cid=cid,
            X_train=X_train,
            y_train=y_train,
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=output_dim,
            batch_size=batch_size,
            learning_rate=learning_rate,
            local_epochs=local_epochs,
        )
        print(
            f"  ⚠  Client {cid} initialised as MALICIOUS "
            f"[{type(attack).__name__}]"
        )

    # ------------------------------------------------------------------
    # Override fit() to inject attack hooks
    # ------------------------------------------------------------------

    def fit(
        self,
        parameters: List[np.ndarray],
        config: Dict,
    ) -> Tuple[List[np.ndarray], int, Dict]:
        """
        Perform a poisoned local training round.

        Steps:
            1. Load global parameters into local model.
            2. Snapshot global parameters (needed for update-manipulation attacks).
            3. Apply ``attack.poison_data()`` to build a poisoned DataLoader.
            4. Train on poisoned data for ``local_epochs`` epochs.
            5. Apply ``attack.poison_update()`` to the trained parameters.
            6. Return poisoned parameters to the server.

        Args:
            parameters: Global model parameters received from the server.
            config:     Round configuration dict (passed through from Flower).

        Returns:
            Tuple of (poisoned_parameters, num_samples, metrics).
        """
        # Step 1 — synchronise local model with global weights
        set_model_parameters(self.model, parameters)

        # Step 2 — snapshot global params for delta-based attacks
        global_params_snapshot: List[np.ndarray] = [p.copy() for p in parameters]

        # Step 3 — poison local training data
        X_poisoned, y_poisoned = self._attack.poison_data(
            self._X_raw.copy(), self._y_raw.copy()
        )

        # Rebuild DataLoader on poisoned data
        X_tensor = torch.FloatTensor(X_poisoned)
        y_tensor = torch.FloatTensor(y_poisoned)
        poisoned_dataset = TensorDataset(X_tensor, y_tensor)
        poisoned_loader = DataLoader(
            poisoned_dataset,
            batch_size=self.batch_size,
            shuffle=True,
        )

        # Step 4 — local SGD on poisoned data
        num_samples, loss = train_model(
            self.model,
            poisoned_loader,
            self.local_epochs,
            self.learning_rate,
            self.device,
        )

        # Step 5 — apply update manipulation (sign-flip / scaling)
        local_params: List[np.ndarray] = get_model_parameters(self.model)
        poisoned_params = self._attack.poison_update(
            global_params_snapshot, local_params
        )

        metrics = {"loss": loss}
        return poisoned_params, num_samples, metrics

    @property
    def attack(self) -> BaseAttack:
        """The active attack instance (read-only)."""
        return self._attack
