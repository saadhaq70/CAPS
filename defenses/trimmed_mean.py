"""
Coordinate-wise Trimmed Mean Robust Aggregation Defense.
Reference: Yin et al., "Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates", ICML 2018.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .base import BaseDefense


class TrimmedMeanDefense(BaseDefense):
    """
    Genuine coordinate-wise Trimmed Mean.
    For each model parameter coordinate across all client updates, sorts the values,
    removes the k lowest and k highest values, and computes the mean of the remainder.
    """

    def __init__(
        self,
        k: int = 1,
        trim_fraction: Optional[float] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Trimmed Mean defense.
        
        Args:
            k: Number of extreme values to trim from EACH end on each coordinate.
               For n=5 clients, k=1 removes 1 min and 1 max value (2k < n condition).
            trim_fraction: Optional fraction beta in [0, 0.5) to derive k = floor(beta * n).
            config: Additional configuration dictionary.
        """
        super().__init__(name="Trimmed Mean", config=config)
        self.k = k
        self.trim_fraction = trim_fraction

    @property
    def defense_type(self) -> str:
        return "robust_aggregation"

    @property
    def supports_self_healing(self) -> bool:
        return False

    @property
    def supports_explicit_detection(self) -> bool:
        # Trimmed Mean is purely coordinate-wise robust aggregation.
        # It does not explicitly declare any client as malicious.
        return False

    def reset(self, initial_params: Optional[List[np.ndarray]] = None) -> None:
        pass

    def aggregate(
        self,
        round_num: int,
        client_updates: List[Tuple[int, List[np.ndarray], int]],
        global_params: List[np.ndarray],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Run coordinate-wise Trimmed Mean aggregation.
        """
        n = len(client_updates)
        if n == 0:
            return global_params, {"error": "No client updates received"}

        # Determine k
        k = self.k
        if self.trim_fraction is not None:
            k = int(np.floor(self.trim_fraction * n))

        # Check validity: 2k < n
        if 2 * k >= n:
            raise ValueError(
                f"Trimmed Mean requires 2k < n. With n={n} clients and k={k}, "
                f"trimming {2 * k} values leaves {n - 2 * k} values, which is invalid."
            )

        cids = [cid for cid, _, _ in client_updates]
        num_layers = len(global_params)
        aggregated_params: List[np.ndarray] = []

        # Coordinate-wise trimming across layers
        for layer_idx in range(num_layers):
            # Stack all clients' arrays for this layer along axis 0: shape (n, dim1, dim2, ...)
            layer_stack = np.stack(
                [client_updates[i][1][layer_idx] for i in range(n)],
                axis=0
            )

            # Sort coordinate-wise along axis 0
            sorted_layer = np.sort(layer_stack, axis=0)

            # Trim k lowest and k highest values
            trimmed_layer = sorted_layer[k : n - k]

            # Compute mean of remaining central values
            mean_layer = np.mean(trimmed_layer, axis=0)
            aggregated_params.append(mean_layer)

        metrics = {
            "trim_k": k,
            "effective_trim_fraction": float(k / n),
            "num_clients": n,
            "retained_per_coordinate": n - 2 * k,
            "participating_clients": cids,
        }

        return aggregated_params, metrics
