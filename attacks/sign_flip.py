"""
ASH-FL Phase 2: Sign-Flipping Attack
After local training the malicious client computes the update delta
(local_params - global_params), negates it, then adds it back to
global_params so the server receives a *reversed* gradient signal.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from attacks.base import AttackConfig, BaseAttack


class SignFlipAttack(BaseAttack):
    """
    Sign-flipping (gradient reversal) attack.

    Effect on FedAvg:
        Each malicious client's contribution pushes the global model in the
        exact opposite direction of what benign clients would push it.
        Even a single malicious client can slow convergence; multiple
        malicious clients can drive the model to diverge entirely.
    """

    def __init__(self, config: AttackConfig) -> None:
        """
        Args:
            config: AttackConfig (no extra params required beyond ``enabled``).
        """
        super().__init__(config)

    def poison_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        No data modification — sign flipping acts only on the update.

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
        Negate the update delta: send global - delta instead of global + delta.

        Mathematically:
            delta        = local_params - global_params
            poisoned     = global_params + (-delta)
                         = 2 * global_params - local_params

        Args:
            global_params: Parameters received from server this round.
            local_params:  Parameters after honest local training.

        Returns:
            Poisoned parameters with negated delta.
        """
        poisoned = [
            2.0 * g - l
            for g, l in zip(global_params, local_params)
        ]
        print("  [SignFlipAttack] Update delta negated (gradient reversal applied)")
        return poisoned
