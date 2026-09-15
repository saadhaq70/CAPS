"""
ASH-FL Phase 2: Base Attack Infrastructure
Defines AttackConfig (data-only config container) and BaseAttack (abstract base).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class AttackConfig:
    """
    Flat configuration container for all attack parameters.

    Populated from the ``attack:`` block in sim_config.yaml.
    Every field has a safe default so clean Phase 1 runs are unaffected.
    """

    # Master switch ── set to False to disable all attack behaviour
    enabled: bool = False

    # Which attack to run (one of: label_flip | sign_flip | scaling | backdoor)
    attack_type: str = "label_flip"

    # How many clients are malicious
    num_malicious_clients: int = 1

    # Explicit list of client IDs to mark malicious.
    # If empty the factory will pick the first ``num_malicious_clients`` IDs.
    malicious_client_ids: List[int] = field(default_factory=list)

    # ── Label-flip params ──────────────────────────────────────────────────
    source_label: int = 0   # label to flip FROM
    target_label: int = 1   # label to flip TO

    # ── Scaling-attack params ──────────────────────────────────────────────
    scale_factor: float = 10.0  # multiply update delta by this factor

    # ── Backdoor params ────────────────────────────────────────────────────
    # Indices of features to overwrite with trigger_value
    trigger_feature_indices: List[int] = field(default_factory=lambda: [0, 1])
    trigger_value: float = 1.0          # value stamped onto trigger features
    poison_fraction: float = 0.3        # fraction of local data to poison
    backdoor_target_label: int = 1      # label forced onto poisoned samples

    @classmethod
    def from_dict(cls, d: dict) -> "AttackConfig":
        """
        Build an AttackConfig from the raw dictionary loaded by yaml.safe_load.

        Args:
            d: Dictionary containing the ``attack:`` block keys.

        Returns:
            Populated AttackConfig instance.
        """
        return cls(
            enabled=bool(d.get("enabled", False)),
            attack_type=str(d.get("attack_type", "label_flip")),
            num_malicious_clients=int(d.get("num_malicious_clients", 1)),
            malicious_client_ids=list(d.get("malicious_client_ids", [])),
            source_label=int(d.get("source_label", 0)),
            target_label=int(d.get("target_label", 1)),
            scale_factor=float(d.get("scale_factor", 10.0)),
            trigger_feature_indices=list(d.get("trigger_feature_indices", [0, 1])),
            trigger_value=float(d.get("trigger_value", 1.0)),
            poison_fraction=float(d.get("poison_fraction", 0.3)),
            backdoor_target_label=int(d.get("backdoor_target_label", 1)),
        )


class BaseAttack(abc.ABC):
    """
    Abstract base class for all attack implementations.

    Sub-classes must implement:
      - ``poison_data``   : modify (X, y) before local training.
      - ``poison_update`` : modify returned parameters after local training.

    Both hooks are called inside ``MaliciousClient.fit()``.
    Attacks that only need one hook should return the inputs unchanged from
    the other hook.
    """

    def __init__(self, config: AttackConfig) -> None:
        """
        Args:
            config: Populated AttackConfig for this attack run.
        """
        self.config = config

    @abc.abstractmethod
    def poison_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Optionally modify training data before local training starts.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Label vector of shape (n_samples,).

        Returns:
            (X_poisoned, y_poisoned) — may be identical to inputs.
        """

    @abc.abstractmethod
    def poison_update(
        self,
        global_params: List[np.ndarray],
        local_params: List[np.ndarray],
    ) -> List[np.ndarray]:
        """
        Optionally modify the locally trained parameters before returning them.

        Args:
            global_params: Model parameters received from the server this round.
            local_params:  Model parameters after local training.

        Returns:
            Modified parameter list sent back to the server.
        """
