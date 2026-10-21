"""
FLTrust: Byzantine-Robust Federated Learning via Trust Bootstrapping.
Reference: Cao et al., "FLTrust: Byzantine-robust Federated Learning via Trust Bootstrapping", NDSS 2021.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from .base import BaseDefense
from clients.client import (
    HeartDiseaseNet,
    get_model_parameters,
    set_model_parameters,
    train_model,
)


class FLTrustDefense(BaseDefense):
    """
    FLTrust uses a clean server-side root dataset to compute a trusted baseline update g_0.
    Client updates are evaluated using cosine similarity to g_0 (trust scores) and their
    magnitudes are normalized to ||g_0|| to neutralize scaling attacks.
    """

    def __init__(
        self,
        validation_data: Tuple[np.ndarray, np.ndarray],
        input_dim: int = 13,
        hidden_dim: int = 32,
        output_dim: int = 1,
        learning_rate: float = 0.01,
        local_epochs: int = 3,
        batch_size: int = 16,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize FLTrust defense.
        
        Args:
            validation_data: (X_root, y_root) clean server-side root dataset
            input_dim: Model input features
            hidden_dim: Model hidden layer dimension
            output_dim: Model output dimension
            learning_rate: Server local training learning rate
            local_epochs: Server local training epochs
            batch_size: Server local training batch size
            config: Additional configuration
        """
        super().__init__(name="FLTrust", config=config)
        self.validation_data = validation_data
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.learning_rate = learning_rate
        self.local_epochs = local_epochs
        self.batch_size = batch_size

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.server_model = HeartDiseaseNet(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=output_dim,
        )

        # Prepare server root DataLoader
        X_val, y_val = validation_data
        val_dataset = TensorDataset(
            torch.FloatTensor(X_val),
            torch.FloatTensor(y_val),
        )
        self.root_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        self.last_trust_scores: Dict[int, float] = {}
        self.last_cosine_sims: Dict[int, float] = {}
        self.last_aggregation_weights: Dict[int, float] = {}
        self.last_server_norm: float = 0.0

    @property
    def defense_type(self) -> str:
        return "trust_weighted"

    @property
    def supports_self_healing(self) -> bool:
        return False

    @property
    def supports_explicit_detection(self) -> bool:
        # FLTrust downweights suspicious updates via trust scores,
        # but does not explicitly categorize clients into malicious classes.
        return False

    def reset(self, initial_params: Optional[List[np.ndarray]] = None) -> None:
        self.last_trust_scores = {}
        self.last_cosine_sims = {}
        self.last_aggregation_weights = {}
        self.last_server_norm = 0.0
        if initial_params is not None:
            set_model_parameters(self.server_model, initial_params)

    @staticmethod
    def _flatten(params: List[np.ndarray]) -> np.ndarray:
        return np.concatenate([p.ravel() for p in params])

    def _compute_server_update(
        self,
        global_params: List[np.ndarray],
        round_num: int = 1,
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        """
        Train on clean server root data from global_params to obtain trusted update g_0.
        
        Returns:
            Tuple of (server_trained_params, server_delta_g0)
        """
        # Ensure deterministic server training
        seed = int(self.config.get("random_seed", 42)) + round_num
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        set_model_parameters(self.server_model, global_params)
        train_model(
            self.server_model,
            self.root_loader,
            epochs=self.local_epochs,
            learning_rate=self.learning_rate,
            device=self.device,
            optimizer_type="adam",
        )
        server_trained_params = get_model_parameters(self.server_model)
        server_delta = [
            s_param - g_param
            for s_param, g_param in zip(server_trained_params, global_params)
        ]
        return server_trained_params, server_delta

    def aggregate(
        self,
        round_num: int,
        client_updates: List[Tuple[int, List[np.ndarray], int]],
        global_params: List[np.ndarray],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Run FLTrust aggregation.
        """
        n = len(client_updates)
        if n == 0:
            return global_params, {"error": "No client updates received"}

        # Step 1: Server computes trusted update g_0
        server_trained_params, g0_delta = self._compute_server_update(global_params, round_num=round_num)
        flat_g0 = self._flatten(g0_delta)
        norm_g0 = float(np.linalg.norm(flat_g0))
        self.last_server_norm = norm_g0

        cids = [cid for cid, _, _ in client_updates]
        client_deltas: List[List[np.ndarray]] = []
        flat_client_deltas: List[np.ndarray] = []
        client_norms: List[float] = []

        # Step 2: Compute client deltas g_i and norms
        for _, params, _ in client_updates:
            delta = [p - g for p, g in zip(params, global_params)]
            client_deltas.append(delta)
            flat_d = self._flatten(delta)
            flat_client_deltas.append(flat_d)
            client_norms.append(float(np.linalg.norm(flat_d)))

        # Step 3: Compute Cosine Similarity and Trust Scores TS_i = max(0, cos(g_i, g_0))
        trust_scores: List[float] = []
        cos_sims: List[float] = []

        for i in range(n):
            norm_gi = client_norms[i]
            if norm_g0 > 1e-9 and norm_gi > 1e-9:
                cos_val = float(np.dot(flat_client_deltas[i], flat_g0) / (norm_gi * norm_g0))
                # Clip numerical inaccuracies
                cos_val = max(-1.0, min(1.0, cos_val))
            else:
                cos_val = 0.0

            cos_sims.append(cos_val)
            ts = max(0.0, cos_val)  # ReLU of cosine similarity
            trust_scores.append(ts)

        self.last_cosine_sims = {cids[i]: cos_sims[i] for i in range(n)}
        self.last_trust_scores = {cids[i]: trust_scores[i] for i in range(n)}

        # Step 4: Normalize client update magnitudes to ||g_0||
        # \tilde{g}_i = (||g_0|| / ||g_i||) * g_i
        normalized_client_deltas: List[List[np.ndarray]] = []
        for i in range(n):
            norm_gi = client_norms[i]
            if norm_gi > 1e-9 and norm_g0 > 1e-9:
                scale_ratio = norm_g0 / norm_gi
                normed_delta = [scale_ratio * layer_d for layer_d in client_deltas[i]]
            else:
                normed_delta = [np.zeros_like(layer_d) for layer_d in client_deltas[i]]
            normalized_client_deltas.append(normed_delta)

        # Step 5: Trust-weighted aggregation
        total_trust = sum(trust_scores)
        aggregated_params: List[np.ndarray] = []
        num_layers = len(global_params)

        if total_trust > 1e-9:
            # Normalized aggregation weights
            weights = [ts / total_trust for ts in trust_scores]
            self.last_aggregation_weights = {cids[i]: weights[i] for i in range(n)}

            # Aggregated delta = sum_i (weights[i] * \tilde{g}_i)
            for layer_idx in range(num_layers):
                agg_delta = np.zeros_like(global_params[layer_idx])
                for i in range(n):
                    agg_delta += weights[i] * normalized_client_deltas[i][layer_idx]
                aggregated_params.append(global_params[layer_idx] + agg_delta)
        else:
            # Fallback: all client updates untrusted; use server model update
            self.last_aggregation_weights = {cids[i]: 0.0 for i in range(n)}
            aggregated_params = [p.copy() for p in server_trained_params]

        metrics = {
            "trust_scores": self.last_trust_scores,
            "cosine_similarities": self.last_cosine_sims,
            "aggregation_weights": self.last_aggregation_weights,
            "server_update_norm": norm_g0,
            "client_update_norms": {cids[i]: client_norms[i] for i in range(n)},
            "total_trust": total_trust,
            "root_samples": len(self.validation_data[0]),
        }

        return aggregated_params, metrics
