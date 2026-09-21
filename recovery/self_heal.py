"""
Self-Healing Controller: FSM-based recovery orchestration.
States: NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

from .health_monitor import HealthMonitor
from .checkpoint_manager import CheckpointManager


class HealingState(Enum):
    """Finite state machine states for self-healing."""

    NORMAL = "normal"  # Healthy operation
    MONITOR = "monitor"  # Degradation detected, monitoring
    RECOVERY = "recovery"  # Active recovery in progress
    VALIDATE = "validate"  # Validating recovered model
    RESUME = "resume"  # Resuming normal operation


class SelfHealingController:
    """
    Orchestrates self-healing process using FSM.
    
    Recovery flow:
    1. Detect degradation (via HealthMonitor)
    2. Identify suspicious clients (via DPS)
    3. Restore last trusted checkpoint
    4. Quarantine suspicious clients (down-weight)
    5. Retrain for N rounds
    6. Validate recovered model
    7. Accept if improved, else expand quarantine or rollback further
    """

    def __init__(
        self,
        config: Dict,
        health_monitor: Optional[HealthMonitor] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        recovery_rounds: int = 3,
        quarantine_window: int = 5,
        suspicious_weight: float = 0.1,
        max_recovery_attempts: int = 3,
    ):
        """
        Args:
            config: Global configuration dict
            health_monitor: HealthMonitor instance (created if None)
            checkpoint_manager: CheckpointManager instance (created if None)
            recovery_rounds: Number of rounds to retrain during recovery
            quarantine_window: Number of rounds to quarantine suspicious clients
            suspicious_weight: Weight multiplier for suspicious clients (0.0-1.0)
            max_recovery_attempts: Max times to attempt recovery before giving up
        """
        self.config = config
        self.health_monitor = health_monitor or HealthMonitor()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()

        self.recovery_rounds = recovery_rounds
        self.quarantine_window = quarantine_window
        self.suspicious_weight = suspicious_weight
        self.max_recovery_attempts = max_recovery_attempts

        # State machine
        self.state = HealingState.NORMAL
        self.state_entry_round = 0

        # Recovery tracking
        self.quarantined_clients: set = set()
        self.quarantine_expiry: Dict[int, int] = {}  # client_id -> expiry_round
        self.recovery_attempt_count = 0
        self.recovery_start_round = 0
        self.pre_recovery_metrics: Optional[Dict[str, float]] = None
        self.candidate_params: Optional[List[np.ndarray]] = None

    def update(
        self,
        round_num: int,
        candidate_params: List[np.ndarray],
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]] = None,
        reputation: Optional[Dict[int, float]] = None,
        client_updates: Optional[List] = None,
    ) -> Tuple[List[np.ndarray], str]:
        """
        Main update loop called after each aggregation round.

        Args:
            round_num: Current round number
            candidate_params: Aggregated model parameters
            metrics: Current round metrics
            dps_dict: Dynamic Poisoning Scores per client
            reputation: Client reputation scores (optional)
            client_updates: Raw client updates (optional, for future use)

        Returns:
            Tuple of (final_params, status_message)
        """
        # Update quarantine expiry
        self._update_quarantine(round_num)

        # Check if model is healthy
        is_healthy = self.health_monitor.is_healthy(metrics, dps_dict)

        # Save checkpoint if healthy
        if is_healthy and self.state == HealingState.NORMAL:
            self.checkpoint_manager.save_if_healthy(
                round_num, candidate_params, metrics, True, reputation
            )
            self.health_monitor.mark_as_trusted(candidate_params)

        # FSM transitions
        if self.state == HealingState.NORMAL:
            return self._handle_normal_state(
                round_num, candidate_params, metrics, dps_dict
            )

        elif self.state == HealingState.MONITOR:
            return self._handle_monitor_state(
                round_num, candidate_params, metrics, dps_dict
            )

        elif self.state == HealingState.RECOVERY:
            return self._handle_recovery_state(
                round_num, candidate_params, metrics, dps_dict
            )

        elif self.state == HealingState.VALIDATE:
            return self._handle_validate_state(
                round_num, candidate_params, metrics, dps_dict
            )

        elif self.state == HealingState.RESUME:
            return self._handle_resume_state(round_num, candidate_params, metrics)

        return candidate_params, f"State: {self.state.value}"

    def _handle_normal_state(
        self,
        round_num: int,
        params: List[np.ndarray],
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]],
    ) -> Tuple[List[np.ndarray], str]:
        """Handle NORMAL state."""
        # Check if recovery should be triggered
        should_recover = self.health_monitor.should_trigger_recovery(
            metrics, dps_dict, params
        )

        if should_recover:
            print(f"\n[SelfHealing] Round {round_num}: DEGRADATION DETECTED")
            print(f"  Transitioning NORMAL → MONITOR")
            self.state = HealingState.MONITOR
            self.state_entry_round = round_num
            self.candidate_params = params
            return params, "Degradation detected, entering monitoring"

        return params, "Healthy operation"

    def _handle_monitor_state(
        self,
        round_num: int,
        params: List[np.ndarray],
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]],
    ) -> Tuple[List[np.ndarray], str]:
        """Handle MONITOR state - verify degradation persists."""
        # Stay in monitor for 1 round to confirm
        if round_num - self.state_entry_round < 1:
            return params, "Monitoring for confirmation"

        # Check if still degraded
        still_degraded = self.health_monitor.should_trigger_recovery(
            metrics, dps_dict, params
        )

        if not still_degraded:
            print(f"[SelfHealing] Round {round_num}: False alarm, returning to NORMAL")
            self.state = HealingState.NORMAL
            return params, "False alarm resolved"

        # Confirmed degradation - start recovery
        print(f"[SelfHealing] Round {round_num}: Degradation confirmed")
        print(f"  Transitioning MONITOR → RECOVERY")
        self._initiate_recovery(round_num, metrics, dps_dict)
        return self._execute_recovery(round_num)

    def _handle_recovery_state(
        self,
        round_num: int,
        params: List[np.ndarray],
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]],
    ) -> Tuple[List[np.ndarray], str]:
        """Handle RECOVERY state - retraining from checkpoint."""
        rounds_in_recovery = round_num - self.recovery_start_round

        if rounds_in_recovery < self.recovery_rounds:
            # Still retraining - use aggregated params but quarantine is active
            return params, f"Recovery in progress ({rounds_in_recovery}/{self.recovery_rounds})"

        # Recovery rounds complete - move to validation
        print(f"[SelfHealing] Round {round_num}: Recovery complete")
        print(f"  Transitioning RECOVERY → VALIDATE")
        self.state = HealingState.VALIDATE
        self.state_entry_round = round_num
        return params, "Recovery complete, entering validation"

    def _handle_validate_state(
        self,
        round_num: int,
        params: List[np.ndarray],
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]],
    ) -> Tuple[List[np.ndarray], str]:
        """Handle VALIDATE state - check if recovery succeeded."""
        # Compare current metrics with pre-recovery
        if self.pre_recovery_metrics is None:
            # No baseline - accept recovery
            self._accept_recovery(round_num, params, metrics)
            return params, "Recovery accepted (no baseline)"

        current_acc = metrics.get("accuracy", 0.0)
        pre_acc = self.pre_recovery_metrics.get("accuracy", 0.0)

        improvement = current_acc - pre_acc

        if improvement > 0.01:  # Meaningful improvement
            print(f"[SelfHealing] Round {round_num}: Recovery SUCCESSFUL")
            print(f"  Accuracy improved: {pre_acc:.3f} → {current_acc:.3f}")
            self._accept_recovery(round_num, params, metrics)
            return params, f"Recovery successful (+{improvement:.3f} accuracy)"

        else:
            print(f"[SelfHealing] Round {round_num}: Recovery FAILED")
            print(f"  Accuracy: {pre_acc:.3f} → {current_acc:.3f}")

            self.recovery_attempt_count += 1

            if self.recovery_attempt_count >= self.max_recovery_attempts:
                print(f"  Max recovery attempts reached, giving up")
                self._accept_recovery(round_num, params, metrics)
                return params, "Recovery failed - max attempts reached"

            # Try expanding quarantine
            print(f"  Attempt {self.recovery_attempt_count}/{self.max_recovery_attempts}")
            print(f"  Expanding quarantine and retrying...")
            self._expand_quarantine(dps_dict)
            self.state = HealingState.RECOVERY
            self.recovery_start_round = round_num
            return self._execute_recovery(round_num)

    def _handle_resume_state(
        self,
        round_num: int,
        params: List[np.ndarray],
        metrics: Dict[str, float],
    ) -> Tuple[List[np.ndarray], str]:
        """Handle RESUME state - transition back to normal."""
        print(f"[SelfHealing] Round {round_num}: Resuming normal operation")
        self.state = HealingState.NORMAL
        return params, "Resumed normal operation"

    def _initiate_recovery(
        self,
        round_num: int,
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]],
    ) -> None:
        """Initiate recovery process."""
        self.recovery_attempt_count += 1
        self.recovery_start_round = round_num
        self.pre_recovery_metrics = metrics.copy()

        # Identify suspicious clients via DPS
        if dps_dict:
            self._identify_suspicious_clients(round_num, dps_dict)

        print(f"[SelfHealing] Quarantined clients: {self.quarantined_clients}")

    def _identify_suspicious_clients(
        self, round_num: int, dps_dict: Dict[int, float]
    ) -> None:
        """Identify and quarantine suspicious clients."""
        # Sort clients by DPS (highest first)
        sorted_clients = sorted(dps_dict.items(), key=lambda x: x[1], reverse=True)

        # Quarantine top clients above threshold
        threshold = self.health_monitor.dps_threshold
        for client_id, dps in sorted_clients:
            if dps > threshold:
                self.quarantined_clients.add(client_id)
                self.quarantine_expiry[client_id] = (
                    round_num + self.quarantine_window
                )

    def _expand_quarantine(self, dps_dict: Optional[Dict[int, float]]) -> None:
        """Expand quarantine to include more clients."""
        if not dps_dict:
            return

        # Lower threshold to quarantine more clients
        threshold = self.health_monitor.dps_threshold * 0.7
        for client_id, dps in dps_dict.items():
            if dps > threshold and client_id not in self.quarantined_clients:
                self.quarantined_clients.add(client_id)
                print(f"  Expanded quarantine: added client {client_id}")

    def _execute_recovery(self, round_num: int) -> Tuple[List[np.ndarray], str]:
        """Restore checkpoint and start recovery."""
        result = self.checkpoint_manager.restore_last_trusted()

        if result is None:
            print(f"[SelfHealing] WARNING: No checkpoint available!")
            self.state = HealingState.NORMAL
            return self.candidate_params or [], "No checkpoint - continuing"

        checkpoint_round, restored_params, checkpoint_metrics = result

        print(f"[SelfHealing] Restored checkpoint from round {checkpoint_round}")
        print(f"  Checkpoint accuracy: {checkpoint_metrics.get('accuracy', 0):.3f}")

        self.state = HealingState.RECOVERY
        return restored_params, f"Restored checkpoint from round {checkpoint_round}"

    def _accept_recovery(
        self, round_num: int, params: List[np.ndarray], metrics: Dict[str, float]
    ) -> None:
        """Accept recovery and transition to RESUME."""
        self.state = HealingState.RESUME
        self.recovery_attempt_count = 0
        self.pre_recovery_metrics = None
        self.candidate_params = None

        # Save as new trusted checkpoint
        self.checkpoint_manager.save_if_healthy(
            round_num, params, metrics, True, None
        )
        self.health_monitor.mark_as_trusted(params)

        # Keep quarantine active for a few more rounds
        print(f"[SelfHealing] Recovery accepted, quarantine remains active")

    def _update_quarantine(self, round_num: int) -> None:
        """Remove clients from quarantine if window expired."""
        expired = [
            cid
            for cid, expiry in self.quarantine_expiry.items()
            if round_num >= expiry
        ]

        for cid in expired:
            self.quarantined_clients.discard(cid)
            del self.quarantine_expiry[cid]
            print(f"[SelfHealing] Client {cid} released from quarantine")

    def is_client_quarantined(self, client_id: int) -> bool:
        """Check if a client is currently quarantined."""
        return client_id in self.quarantined_clients

    def get_client_weight_multiplier(self, client_id: int) -> float:
        """
        Get weight multiplier for a client (used in aggregation).

        Args:
            client_id: Client identifier

        Returns:
            Weight multiplier (1.0 = normal, 0.0-1.0 = penalized)
        """
        if client_id in self.quarantined_clients:
            return self.suspicious_weight
        return 1.0

    def get_state(self) -> str:
        """Get current FSM state."""
        return self.state.value

    def get_status_summary(self) -> Dict:
        """Get detailed status summary."""
        return {
            "state": self.state.value,
            "quarantined_clients": list(self.quarantined_clients),
            "recovery_attempts": self.recovery_attempt_count,
            "checkpoints": len(self.checkpoint_manager.checkpoints),
        }
