"""
Checkpoint Manager: Saves and restores trusted model states.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass, field
from collections import deque


@dataclass
class Checkpoint:
    """Container for a saved checkpoint."""

    round_num: int
    model_params: List[np.ndarray]
    metrics: Dict[str, float]
    reputation: Optional[Dict[int, float]] = None
    timestamp: Optional[float] = None

    def copy_params(self) -> List[np.ndarray]:
        """Return a deep copy of model parameters."""
        return [p.copy() for p in self.model_params]


class CheckpointManager:
    """
    Manages checkpoints of healthy global models.
    Keeps a rolling window of recent trusted checkpoints.
    """

    def __init__(self, max_checkpoints: int = 3):
        """
        Args:
            max_checkpoints: Maximum number of checkpoints to retain
        """
        self.max_checkpoints = max_checkpoints
        self.checkpoints: deque[Checkpoint] = deque(maxlen=max_checkpoints)
        self.last_saved_round: int = -1

    def save_if_healthy(
        self,
        round_num: int,
        model_params: List[np.ndarray],
        metrics: Dict[str, float],
        is_healthy: bool,
        reputation: Optional[Dict[int, float]] = None,
    ) -> bool:
        """
        Save checkpoint if model is healthy.

        Args:
            round_num: Current round number
            model_params: Model parameters to save
            metrics: Current metrics
            is_healthy: Whether the model is healthy
            reputation: Optional client reputation scores

        Returns:
            True if checkpoint was saved
        """
        if not is_healthy:
            return False

        # Don't save duplicate rounds
        if round_num == self.last_saved_round:
            return False

        import time

        checkpoint = Checkpoint(
            round_num=round_num,
            model_params=[p.copy() for p in model_params],
            metrics=metrics.copy(),
            reputation=reputation.copy() if reputation else None,
            timestamp=time.time(),
        )

        self.checkpoints.append(checkpoint)
        self.last_saved_round = round_num

        print(
            f"  [CheckpointMgr] Saved checkpoint for round {round_num} "
            f"(accuracy: {metrics.get('accuracy', 0):.3f})"
        )
        return True

    def restore_last_trusted(self) -> Optional[Tuple[int, List[np.ndarray], Dict[str, float]]]:
        """
        Restore the most recent trusted checkpoint.

        Returns:
            Tuple of (round_num, model_params, metrics) or None if no checkpoint exists
        """
        if not self.checkpoints:
            return None

        checkpoint = self.checkpoints[-1]
        print(
            f"  [CheckpointMgr] Restoring checkpoint from round {checkpoint.round_num} "
            f"(accuracy: {checkpoint.metrics.get('accuracy', 0):.3f})"
        )

        return (
            checkpoint.round_num,
            checkpoint.copy_params(),
            checkpoint.metrics.copy(),
        )

    def restore_nth_trusted(self, n: int = 1) -> Optional[Tuple[int, List[np.ndarray], Dict[str, float]]]:
        """
        Restore the n-th most recent checkpoint (1 = most recent).

        Args:
            n: Which checkpoint to restore (1-indexed)

        Returns:
            Tuple of (round_num, model_params, metrics) or None
        """
        if n < 1 or n > len(self.checkpoints):
            return None

        checkpoint = self.checkpoints[-n]
        print(
            f"  [CheckpointMgr] Restoring checkpoint {n} from round {checkpoint.round_num}"
        )

        return (
            checkpoint.round_num,
            checkpoint.copy_params(),
            checkpoint.metrics.copy(),
        )

    def get_history(self) -> List[Dict[str, any]]:
        """
        Get history of all checkpoints.

        Returns:
            List of checkpoint summaries
        """
        return [
            {
                "round": cp.round_num,
                "accuracy": cp.metrics.get("accuracy", 0.0),
                "loss": cp.metrics.get("loss", 0.0),
                "timestamp": cp.timestamp,
            }
            for cp in self.checkpoints
        ]

    def has_checkpoints(self) -> bool:
        """Check if any checkpoints exist."""
        return len(self.checkpoints) > 0

    def get_latest_round(self) -> int:
        """Get the round number of the most recent checkpoint."""
        return self.checkpoints[-1].round_num if self.checkpoints else -1

    def clear(self) -> None:
        """Clear all checkpoints."""
        self.checkpoints.clear()
        self.last_saved_round = -1
        print("  [CheckpointMgr] Cleared all checkpoints")
