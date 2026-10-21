"""
Base Defense Interface for Federated Learning Defense Comparison.
Provides a unified abstract class for Multi-Krum, Trimmed Mean, FLTrust, and ASH-FL.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class BaseDefense(abc.ABC):
    """
    Abstract base class for all federated learning defense strategies.
    
    Guarantees that all defenses receive identical client updates and produce
    standardized output formats.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the defense strategy.
        
        Args:
            name: Human-readable name of the defense
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}

    @property
    @abc.abstractmethod
    def defense_type(self) -> str:
        """
        Type of defense mechanism:
        - 'robust_aggregation': filters or trims updates in parameter space (e.g. Multi-Krum, Trimmed Mean)
        - 'trust_weighted': weights updates using clean root server data (e.g. FLTrust)
        - 'self_healing': multi-layer detection, quarantine, and FSM recovery (e.g. ASH-FL)
        """
        pass

    @property
    @abc.abstractmethod
    def supports_self_healing(self) -> bool:
        """Whether this defense provides autonomous rollback/self-healing."""
        pass

    @property
    @abc.abstractmethod
    def supports_explicit_detection(self) -> bool:
        """Whether this defense explicitly labels individual clients as malicious."""
        pass

    @abc.abstractmethod
    def reset(self, initial_params: Optional[List[np.ndarray]] = None) -> None:
        """
        Reset internal state between runs.
        
        Args:
            initial_params: Optional initial global model parameters
        """
        pass

    @abc.abstractmethod
    def aggregate(
        self,
        round_num: int,
        client_updates: List[Tuple[int, List[np.ndarray], int]],
        global_params: List[np.ndarray],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Aggregate client updates into new global parameters.
        
        Args:
            round_num: Current federated round (1-indexed)
            client_updates: List of tuples (client_id, updated_parameters, num_samples)
            global_params: Global model parameters at start of this round
            
        Returns:
            Tuple of:
                - new_global_params: List of aggregated parameter arrays
                - defense_metrics: Dictionary of defense-specific diagnostic metrics
        """
        pass
