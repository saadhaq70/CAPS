"""
ASH-FL Phase 2: Backdoor Attack
Injects a fixed trigger pattern into a fraction of the malicious client's
local training data and forces those samples to a target label.
Clean-data accuracy is largely preserved; the global model learns a hidden
trigger → target mapping that persists across future rounds.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from attacks.base import AttackConfig, BaseAttack


class BackdoorAttack(BaseAttack):
    """
    Backdoor (trojan / trigger injection) attack.

    Mechanism:
        A random subset of ``poison_fraction`` training samples has its
        ``trigger_feature_indices`` columns overwritten with ``trigger_value``
        and its label set to ``backdoor_target_label``.  The clean portion of
        the data is untouched, so the client's loss on benign inputs stays
        low.  After aggregation the global model activates on the trigger.

    Effect on FedAvg:
        Clean-data accuracy remains close to baseline (stealthy).
        Trigger-stamped test inputs are mis-classified to the target label
        with high probability — the Attack Success Rate (ASR).
    """

    def __init__(self, config: AttackConfig) -> None:
        """
        Args:
            config: Must have ``trigger_feature_indices``, ``trigger_value``,
                    ``poison_fraction``, and ``backdoor_target_label`` set.
        """
        super().__init__(config)

    def poison_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Stamp the trigger on ``poison_fraction`` of the samples.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Label vector of shape (n_samples,).

        Returns:
            (X_poisoned, y_poisoned) with trigger-injected rows.
        """
        X_p = X.copy()
        y_p = y.copy()

        n_total = len(X_p)
        n_poison = max(1, int(n_total * self.config.poison_fraction))

        # Pick a random subset (reproducible within the numpy global seed)
        poison_indices = np.random.choice(n_total, size=n_poison, replace=False)

        # Stamp trigger pattern
        for feat_idx in self.config.trigger_feature_indices:
            X_p[poison_indices, feat_idx] = self.config.trigger_value

        # Force target label
        y_p[poison_indices] = float(self.config.backdoor_target_label)

        print(
            f"  [BackdoorAttack] Poisoned {n_poison}/{n_total} samples "
            f"(trigger features {self.config.trigger_feature_indices} = "
            f"{self.config.trigger_value}, label → {self.config.backdoor_target_label})"
        )
        return X_p, y_p

    def poison_update(
        self,
        global_params: List[np.ndarray],
        local_params: List[np.ndarray],
    ) -> List[np.ndarray]:
        """
        No update manipulation — the backdoor is embedded through data only.

        Args:
            global_params: Ignored.
            local_params:  Returned as-is.

        Returns:
            Unmodified ``local_params``.
        """
        return local_params

    # ── Utility for external evaluation ───────────────────────────────────

    def stamp_trigger(self, X: np.ndarray) -> np.ndarray:
        """
        Apply the trigger to a feature matrix for Attack-Success-Rate testing.

        Args:
            X: Clean feature matrix of shape (n_samples, n_features).

        Returns:
            Copy of X with trigger features overwritten.
        """
        X_triggered = X.copy()
        for feat_idx in self.config.trigger_feature_indices:
            X_triggered[:, feat_idx] = self.config.trigger_value
        return X_triggered
