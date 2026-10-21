"""
Federated Learning Defenses Package.
Contains implementations of Multi-Krum, Trimmed Mean, FLTrust, and ASH-FL,
along with the common comparison runner and standardized result containers.
"""

from .base import BaseDefense
from .multi_krum import MultiKrumDefense
from .trimmed_mean import TrimmedMeanDefense
from .fltrust import FLTrustDefense
from .ash_fl import ASHFLDefense
from .runner import (
    ComparisonRunner,
    ExperimentConfig,
    DefenseResult,
    ComparisonResult,
    compute_backdoor_asr,
)

__all__ = [
    "BaseDefense",
    "MultiKrumDefense",
    "TrimmedMeanDefense",
    "FLTrustDefense",
    "ASHFLDefense",
    "ComparisonRunner",
    "ExperimentConfig",
    "DefenseResult",
    "ComparisonResult",
    "compute_backdoor_asr",
]
