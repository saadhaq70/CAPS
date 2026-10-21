"""
Multi-Krum Robust Aggregation Defense.
Reference: Blanchard et al., "Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent", NeurIPS 2017.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .base import BaseDefense


class MultiKrumDefense(BaseDefense):
    """
    Multi-Krum selects a subset of client updates that are closest to the majority
    based on pairwise Euclidean distances, excluding potential Byzantine outliers.
    """

    def __init__(
        self,
        f: int = 1,
        m: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Multi-Krum.
        
        Args:
            f: Assumed maximum number of Byzantine/malicious clients.
               For n=5 clients, f must be <= 1 to satisfy n >= 2f + 3.
            m: Number of client updates to select for aggregation.
               Defaults to n - f if None.
            config: Additional optional config parameters.
        """
        super().__init__(name="Multi-Krum", config=config)
        self.f = f
        self.m = m
        self.last_selected_clients: List[int] = []
        self.last_krum_scores: Dict[int, float] = {}

    @property
    def defense_type(self) -> str:
        return "robust_aggregation"

    @property
    def supports_self_healing(self) -> bool:
        return False

    @property
    def supports_explicit_detection(self) -> bool:
        # Multi-Krum is an aggregation defense; it selects majority updates
        # rather than explicitly declaring rejected clients as malicious.
        return False

    def reset(self, initial_params: Optional[List[np.ndarray]] = None) -> None:
        self.last_selected_clients = []
        self.last_krum_scores = {}

    @staticmethod
    def _flatten(params: List[np.ndarray]) -> np.ndarray:
        return np.concatenate([p.ravel() for p in params])

    def aggregate(
        self,
        round_num: int,
        client_updates: List[Tuple[int, List[np.ndarray], int]],
        global_params: List[np.ndarray],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Run Multi-Krum aggregation on client updates.
        """
        n = len(client_updates)
        if n == 0:
            return global_params, {"error": "No client updates received"}

        # Mathematical constraint check: n >= 2f + 3
        max_f = max(0, (n - 3) // 2)
        if n < 2 * self.f + 3:
            raise ValueError(
                f"Multi-Krum mathematical constraint violated: requires n >= 2f + 3. "
                f"With n={n} clients, f={self.f} is invalid. "
                f"For {n} clients, maximum allowable f is {max_f}."
            )

        # Number of neighbors to consider for Krum score
        num_neighbors = n - self.f - 2

        # Number of candidates to select
        m = self.m if self.m is not None else (n - self.f)
        m = max(1, min(m, n))

        # Flatten updates for distance calculation
        cids = [cid for cid, _, _ in client_updates]
        flat_vectors = [self._flatten(params) for _, params, _ in client_updates]

        # Pairwise squared Euclidean distance matrix
        dist_matrix = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            for j in range(i + 1, n):
                d2 = float(np.sum((flat_vectors[i] - flat_vectors[j]) ** 2))
                dist_matrix[i, j] = d2
                dist_matrix[j, i] = d2

        # Compute Krum score for each client: sum of distances to num_neighbors closest other clients
        krum_scores = []
        for i in range(n):
            # All distances from client i to other clients
            other_distances = [dist_matrix[i, j] for j in range(n) if j != i]
            other_distances.sort()
            score = float(sum(other_distances[:num_neighbors]))
            krum_scores.append(score)

        self.last_krum_scores = {cids[i]: krum_scores[i] for i in range(n)}

        # Multi-Krum selection: iteratively select m clients with the smallest Krum scores
        candidate_indices = list(range(n))
        selected_indices: List[int] = []

        # Sort candidate indices by their precomputed Krum score ascending
        sorted_candidates = sorted(candidate_indices, key=lambda idx: krum_scores[idx])
        selected_indices = sorted_candidates[:m]

        self.last_selected_clients = [cids[idx] for idx in selected_indices]
        excluded_clients = [cids[idx] for idx in range(n) if idx not in selected_indices]

        # Aggregate selected updates (arithmetic mean across selected clients)
        aggregated_params: List[np.ndarray] = []
        num_layers = len(global_params)

        for layer_idx in range(num_layers):
            layer_updates = [client_updates[idx][1][layer_idx] for idx in selected_indices]
            avg_layer = np.mean(layer_updates, axis=0)
            aggregated_params.append(avg_layer)

        # Calculate implicit aggregation weights (1/m for selected, 0 for excluded)
        aggregation_weights = {
            cids[idx]: (1.0 / m if idx in selected_indices else 0.0)
            for idx in range(n)
        }

        metrics = {
            "selected_clients": self.last_selected_clients,
            "excluded_clients": excluded_clients,
            "krum_scores": self.last_krum_scores,
            "aggregation_weights": aggregation_weights,
            "f_byzantine": self.f,
            "m_selected": m,
            "num_neighbors": num_neighbors,
        }

        return aggregated_params, metrics
