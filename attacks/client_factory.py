"""
ASH-FL Phase 2: Extended Client Factory
Replaces ``clients.client.get_client_fn`` when attacks are enabled.
Assigns malicious IDs deterministically (or from explicit config list),
and exposes a ``is_malicious`` ground-truth dict for Phase 3 scoring.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import flwr as fl
import numpy as np

from clients.client import HeartDiseaseClient
from attacks.base import AttackConfig
from attacks import get_attack
from attacks.malicious_client import MaliciousClient


def resolve_malicious_ids(
    attack_config: AttackConfig,
    num_clients_total: int,
) -> List[int]:
    """
    Determine which client IDs are malicious for this run.

    Priority:
      1. Use ``attack_config.malicious_client_ids`` if non-empty.
      2. Otherwise pick the first ``attack_config.num_malicious_clients`` IDs.

    Args:
        attack_config:     Populated AttackConfig from sim_config.yaml.
        num_clients_total: Total number of clients in the federation.

    Returns:
        Sorted list of integer client IDs that will be malicious.

    Raises:
        ValueError: If any explicit ID is out of range.
    """
    if attack_config.malicious_client_ids:
        ids = sorted(set(int(i) for i in attack_config.malicious_client_ids))
        for cid in ids:
            if cid < 0 or cid >= num_clients_total:
                raise ValueError(
                    f"malicious_client_ids contains {cid} which is out of "
                    f"range [0, {num_clients_total - 1}]"
                )
        return ids

    n = min(attack_config.num_malicious_clients, num_clients_total)
    return list(range(n))


def get_client_fn_with_attacks(
    client_data: List[Tuple[np.ndarray, np.ndarray]],
    config: Dict,
    attack_config: AttackConfig,
    per_client_attacks: Dict[int, str] = None,
) -> Tuple[callable, Dict[int, bool]]:
    """
    Build a Flower-compatible client factory that injects malicious clients.
    
    ENHANCED: Supports per-client attack types via per_client_attacks dict.

    If ``attack_config.enabled`` is False, every client is a benign
    HeartDiseaseClient and the function behaves identically to
    ``clients.client.get_client_fn``.

    Args:
        client_data:   List of (X, y) tuples indexed by client ID.
        config:        Hyperparameter dict from sim_config.yaml.
        attack_config: Populated AttackConfig.
        per_client_attacks: Optional dict mapping client_id -> attack_type string
                           (e.g., {0: 'scaling', 1: 'label_flip', 2: 'none'})

    Returns:
        Tuple of:
          - ``client_fn(cid: str) -> fl.client.NumPyClient``
            ready to pass to ``fl.simulation.start_simulation``.
          - ``ground_truth: Dict[int, bool]``
            mapping client_id → is_malicious for Phase 3+ use.
            All values are False when attacks are disabled.
    """
    num_clients = len(client_data)

    if attack_config.enabled:
        if per_client_attacks:
            # Per-client attack configuration
            malicious_ids = [cid for cid, attack_type in per_client_attacks.items() 
                           if attack_type != "none"]
            
            # Create attack instances for each type
            attack_instances = {}
            for attack_type in set(per_client_attacks.values()):
                if attack_type != "none":
                    # Create a new attack config for this specific attack type
                    type_config = AttackConfig(
                        enabled=True,
                        attack_type=attack_type,
                        num_malicious_clients=1,
                        malicious_client_ids=[],
                        source_label=attack_config.source_label,
                        target_label=attack_config.target_label,
                        scale_factor=attack_config.scale_factor,
                        trigger_feature_indices=attack_config.trigger_feature_indices,
                        trigger_value=attack_config.trigger_value,
                        poison_fraction=attack_config.poison_fraction,
                        backdoor_target_label=attack_config.backdoor_target_label
                    )
                    attack_instances[attack_type] = get_attack(type_config)
            
            print(f"  Attack enabled: per-client | Malicious clients: {malicious_ids}")
        else:
            # Legacy: single attack type for all malicious clients
            malicious_ids = resolve_malicious_ids(attack_config, num_clients)
            attack_instances = {attack_config.attack_type: get_attack(attack_config)}
            per_client_attacks = {cid: attack_config.attack_type if cid in malicious_ids else "none" 
                                for cid in range(num_clients)}
            print(f"  Attack enabled: {attack_config.attack_type} | Malicious clients: {malicious_ids}")
    else:
        malicious_ids = []
        attack_instances = {}
        per_client_attacks = {i: "none" for i in range(num_clients)}

    malicious_id_set = set(malicious_ids)

    # Ground-truth map exposed for Phase 3+ detection scoring
    ground_truth: Dict[int, bool] = {
        i: (i in malicious_id_set) for i in range(num_clients)
    }

    # ── Flower client factory ─────────────────────────────────────────────
    def client_fn(cid: str) -> fl.client.NumPyClient:
        """Instantiate a benign or malicious client for the given string ID."""
        client_id = int(cid)
        X_train, y_train = client_data[client_id]

        common_kwargs = dict(
            cid=client_id,
            X_train=X_train,
            y_train=y_train,
            input_dim=config["input_dim"],
            hidden_dim=config["hidden_dim"],
            output_dim=config["output_dim"],
            batch_size=config["batch_size"],
            learning_rate=config["learning_rate"],
            local_epochs=config["local_epochs"],
        )

        if client_id in malicious_id_set:
            # Get the specific attack type for this client
            attack_type = per_client_attacks.get(client_id, "none")
            if attack_type != "none":
                attack = attack_instances[attack_type]
                return MaliciousClient(**common_kwargs, attack=attack)

        client = HeartDiseaseClient(**common_kwargs)
        client.is_malicious = False  # tag benign clients for consistency
        return client

    return client_fn, ground_truth
