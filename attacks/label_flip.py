"""
ASH-FL Phase 2: Label-Flipping Attack
Malicious client flips labels from ``source_label`` to ``target_label``
in its local training set before running the normal SGD loop.
The model update is returned unmodified — only the training signal is corrupted.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from attacks.base import AttackConfig, BaseAttack


class LabelFlipAttack(BaseAttack):
    """
    Label-flipping attack: poison the training labels before local training.

    Effect on FedAvg:
        The malicious client trains a model that maps features incorrectly
        (e.g. heart-disease patients → no disease).  Aggregation pulls the
        global model toward that biased mapping, reducing overall accuracy.
    """

    def __init__(self, config: AttackConfig) -> None:
        """
        Args:
            config: Must have ``source_label`` and ``target_label`` set.
        """
        super().__init__(config)

    def poison_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Flip every occurrence of ``source_label`` to ``target_label``.

        Args:
            X: Feature matrix (unchanged).
            y: Label vector; entries equal to ``source_label`` are flipped.

        Returns:
            (X, y_flipped) where y_flipped has labels replaced.
        """
        y_flipped = y.copy()
        mask = y_flipped == self.config.source_label
        y_flipped[mask] = self.config.target_label
        n_flipped = int(mask.sum())
        print(
            f"  [LabelFlipAttack] Flipped {n_flipped}/{len(y)} labels "
            f"({self.config.source_label} → {self.config.target_label})"
        )
        return X, y_flipped

    def poison_update(
        self,
        global_params: List[np.ndarray],
        local_params: List[np.ndarray],
    ) -> List[np.ndarray]:
        """
        No update manipulation — label flipping acts only on data.

        Args:
            global_params: Ignored.
            local_params:  Returned as-is.

        Returns:
            Unmodified ``local_params``.
        """
        return local_params
