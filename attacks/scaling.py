"""
ASH-FL Phase 2: Scaling Attack
After local training the malicious client amplifies its update delta by
``scale_factor``, making its gradient dominate the FedAvg weighted average.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from attacks.base import AttackConfig, BaseAttack


class ScalingAttack(BaseAttack):
    """
    Scaling (gradient amplification) attack.

    Effect on FedAvg:
        By returning delta * scale_factor the malicious client effectively
        claims that its gradient should count ``scale_factor`` times more
        than the weight implied by its sample count.  With a large enough
        factor a single malicious client can steer the global model almost
        arbitrarily.
    """

    def __init__(self, config: AttackConfig) -> None:
        """
        Args:
            config: Must have ``scale_factor`` set (e.g. 10.0).
        """
        super().__init__(config)

    def poison_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        No data modification — scaling acts only on the returned update.

        Args:
            X: Returned unchanged.
            y: Returned unchanged.

        Returns:
            (X, y) unmodified.
        """
        return X, y

    def poison_update(
        self,
        global_params: List[np.ndarray],
        local_params: List[np.ndarray],
    ) -> List[np.ndarray]:
        """
        Scale the update delta by ``config.scale_factor``.

        Mathematically:
            delta    = local_params - global_params
            poisoned = global_params + scale_factor * delta

        Args:
            global_params: Parameters received from server this round.
            local_params:  Parameters after honest local training.

        Returns:
            Scaled parameter update.
        """
        sf = self.config.scale_factor
        scaled = [
            g + sf * (l - g)
            for g, l in zip(global_params, local_params)
        ]
        print(
            f"  [ScalingAttack] Update delta scaled by {sf}x"
        )
        return scaled
