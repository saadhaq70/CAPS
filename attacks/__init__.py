"""
ASH-FL Phase 2: Attack Harness
Provides four attack types injectable into the FL simulation:
  - LabelFlipAttack   : flip source_label -> target_label before training
  - SignFlipAttack    : negate the model update delta after local training
  - ScalingAttack     : scale the update by a configurable amplification factor
  - BackdoorAttack    : stamp a trigger pattern on a fraction of data with target label

Import surface used by the rest of the project:
    from attacks import AttackConfig, get_attack
    from attacks.malicious_client import MaliciousClient
    from attacks.client_factory import get_client_fn_with_attacks
"""

from attacks.base import AttackConfig, BaseAttack
from attacks.label_flip import LabelFlipAttack
from attacks.sign_flip import SignFlipAttack
from attacks.scaling import ScalingAttack
from attacks.backdoor import BackdoorAttack


_ATTACK_REGISTRY: dict = {
    "label_flip": LabelFlipAttack,
    "sign_flip": SignFlipAttack,
    "scaling": ScalingAttack,
    "backdoor": BackdoorAttack,
}


def get_attack(config: "AttackConfig") -> "BaseAttack":
    """
    Instantiate and return the correct attack object from an AttackConfig.

    Args:
        config: AttackConfig dataclass populated from sim_config.yaml

    Returns:
        Concrete BaseAttack subclass instance

    Raises:
        ValueError: If attack_type is unknown
    """
    attack_type = config.attack_type.lower()
    if attack_type not in _ATTACK_REGISTRY:
        raise ValueError(
            f"Unknown attack_type '{attack_type}'. "
            f"Valid choices: {list(_ATTACK_REGISTRY.keys())}"
        )
    return _ATTACK_REGISTRY[attack_type](config)


__all__ = [
    "AttackConfig",
    "BaseAttack",
    "LabelFlipAttack",
    "SignFlipAttack",
    "ScalingAttack",
    "BackdoorAttack",
    "get_attack",
]
