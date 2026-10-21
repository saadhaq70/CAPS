"""
Health Monitor: Tracks global health signals and triggers recovery.
"""

from typing import Dict, List, Optional
import numpy as np


class HealthMonitor:
    """
    Monitors federated learning health metrics and determines when to trigger recovery.
    Uses rolling baselines to distinguish attacks from normal training noise.
    """

    def __init__(
        self,
        accuracy_drop_threshold: float = 0.15,
        loss_spike_threshold: float = 0.3,
        dps_threshold: float = 0.55,  # IMPROVED: Lowered from 2.0 to 0.55 (normalized)
        suspicious_fraction_threshold: float = 0.3,
        model_drift_threshold: float = 5.0,
        baseline_window: int = 3,
        persistent_dps_threshold: float = 0.45,
        persistent_trust_threshold: float = 0.85,
        persistent_rounds: int = 2,
    ):
        """
        Args:
            accuracy_drop_threshold: Trigger if accuracy drops by this fraction from baseline
            loss_spike_threshold: Trigger if loss increases by this fraction from baseline
            dps_threshold: Max DPS value before flagging as suspicious
            suspicious_fraction_threshold: Trigger if this fraction of clients are suspicious
            model_drift_threshold: L2 distance from last trusted model threshold
            baseline_window: Number of rounds to use for rolling baseline
            persistent_dps_threshold: DPS threshold for persistent malicious client detection
            persistent_trust_threshold: Maximum trust score to confirm persistent malicious client
            persistent_rounds: Consecutive rounds required for persistent malicious detection
        """
        self.accuracy_drop_threshold = accuracy_drop_threshold
        self.loss_spike_threshold = loss_spike_threshold
        self.dps_threshold = dps_threshold  # NOTE: DPS scores are normalized to [0,1]
        self.suspicious_fraction_threshold = suspicious_fraction_threshold
        self.model_drift_threshold = model_drift_threshold
        self.baseline_window = baseline_window
        self.persistent_dps_threshold = persistent_dps_threshold
        self.persistent_trust_threshold = persistent_trust_threshold
        self.persistent_rounds = persistent_rounds

        # History tracking
        self.accuracy_history: List[float] = []
        self.loss_history: List[float] = []
        self.dps_history: List[Dict[int, float]] = []
        self.trusted_model_params: Optional[List[np.ndarray]] = None

    def update_history(
        self,
        accuracy: float,
        loss: float,
        dps_dict: Optional[Dict[int, float]] = None,
    ) -> None:
        """
        Update metric history.

        Args:
            accuracy: Current round's validation accuracy
            loss: Current round's validation loss
            dps_dict: Dynamic Poisoning Scores per client (optional)
        """
        self.accuracy_history.append(accuracy)
        self.loss_history.append(loss)
        if dps_dict:
            self.dps_history.append(dps_dict)

    def get_baseline_accuracy(self) -> Optional[float]:
        """Compute rolling baseline accuracy."""
        if len(self.accuracy_history) < 2:
            return None
        window = self.accuracy_history[-self.baseline_window - 1 : -1]
        return np.mean(window) if window else None

    def get_baseline_loss(self) -> Optional[float]:
        """Compute rolling baseline loss."""
        if len(self.loss_history) < 2:
            return None
        window = self.loss_history[-self.baseline_window - 1 : -1]
        return np.mean(window) if window else None

    def compute_model_drift(
        self, current_params: List[np.ndarray]
    ) -> Optional[float]:
        """
        Compute L2 distance between current model and last trusted model.

        Args:
            current_params: Current global model parameters

        Returns:
            L2 distance or None if no trusted model exists
        """
        if self.trusted_model_params is None:
            return None

        total_dist = 0.0
        for p_curr, p_trust in zip(current_params, self.trusted_model_params):
            total_dist += np.sum((p_curr - p_trust) ** 2)
        return float(np.sqrt(total_dist))

    def get_persistent_suspicious_clients(
        self, reputation: Optional[Dict[int, float]] = None
    ) -> List[int]:
        """
        Identify clients exhibiting persistent suspicious behavior across consecutive rounds.
        A client is flagged if:
          1. Their DPS exceeds persistent_dps_threshold for at least persistent_rounds consecutive rounds.
          2. Their reputation/trust score is <= persistent_trust_threshold (dual-gate requirement).
             Default trust is 1.0 (clean) if not provided in reputation dict.

        Args:
            reputation: Client trust/reputation mapping (client_id -> trust in [0.01, 1.0])

        Returns:
            List of client IDs confirmed as persistently suspicious.
        """
        if len(self.dps_history) < self.persistent_rounds:
            return []

        recent_dps_rounds = self.dps_history[-self.persistent_rounds:]
        current_dps = recent_dps_rounds[-1]
        suspicious_clients: List[int] = []

        for cid in current_dps.keys():
            # Check consecutive rounds of elevated DPS
            is_consecutively_high = all(
                cid in round_dps and round_dps[cid] > self.persistent_dps_threshold
                for round_dps in recent_dps_rounds
            )
            if not is_consecutively_high:
                continue

            # Check reputation / trust condition (dual-gate to prevent false positives)
            client_trust = reputation.get(cid, 1.0) if reputation else 1.0
            if client_trust <= self.persistent_trust_threshold:
                suspicious_clients.append(cid)

        return suspicious_clients

    def should_trigger_recovery(
        self,
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]] = None,
        current_params: Optional[List[np.ndarray]] = None,
        reputation: Optional[Dict[int, float]] = None,
    ) -> bool:
        """
        Determine if recovery should be triggered based on health signals.

        Args:
            metrics: Current round metrics (must include 'accuracy' and 'loss')
            dps_dict: Dynamic Poisoning Scores per client
            current_params: Current global model parameters
            reputation: Client trust/reputation scores (optional, for persistent detection)

        Returns:
            True if recovery should be triggered, False otherwise
        """
        accuracy = metrics.get("accuracy", 0.0)
        loss = metrics.get("loss", float("inf"))

        # Update history
        self.update_history(accuracy, loss, dps_dict)

        # Need enough history for baseline
        if len(self.accuracy_history) < 2:
            return False

        # Check 1: Accuracy drop
        baseline_acc = self.get_baseline_accuracy()
        if baseline_acc is not None:
            acc_drop = baseline_acc - accuracy
            if acc_drop > self.accuracy_drop_threshold:
                print(
                    f"  [HealthMonitor] Accuracy dropped by {acc_drop:.3f} "
                    f"(threshold: {self.accuracy_drop_threshold})"
                )
                return True

        # Check 2: Loss spike
        baseline_loss = self.get_baseline_loss()
        if baseline_loss is not None and baseline_loss > 0:
            loss_increase = (loss - baseline_loss) / baseline_loss
            if loss_increase > self.loss_spike_threshold:
                print(
                    f"  [HealthMonitor] Loss spiked by {loss_increase:.3f} "
                    f"(threshold: {self.loss_spike_threshold})"
                )
                return True

        # Check 3: DPS analysis
        if dps_dict and len(dps_dict) > 0:  # Check dict is not empty
            avg_dps = np.mean(list(dps_dict.values()))
            max_dps = np.max(list(dps_dict.values()))
            num_suspicious = sum(1 for dps in dps_dict.values() if dps > self.dps_threshold)
            fraction_suspicious = num_suspicious / len(dps_dict) if len(dps_dict) > 0 else 0.0

            # Check if max DPS exceeds critical threshold
            # NOTE: DPS is normalized [0,1], so threshold of 0.55 means 55% malicious confidence
            # IMPROVED: More sensitive thresholds for label-flip detection
            if max_dps > 0.55:  # IMPROVED: Lower threshold from 0.6 to 0.55
                print(
                    f"  [HealthMonitor] Max DPS {max_dps:.3f} exceeds critical threshold (0.55)"
                )
                return True
            
            # Also check if any client exceeds the configured threshold even slightly
            if max_dps > self.dps_threshold * 1.05:  # 5% above threshold (was 10%)
                print(
                    f"  [HealthMonitor] Max DPS {max_dps:.3f} exceeds threshold {self.dps_threshold} by 5%+"
                )
                return True

            if fraction_suspicious > self.suspicious_fraction_threshold:
                print(
                    f"  [HealthMonitor] Suspicious client fraction {fraction_suspicious:.2f} "
                    f"exceeds threshold {self.suspicious_fraction_threshold}"
                )
                return True

            # Check 3b: Persistent suspicious clients (Option C)
            persistent_suspicious = self.get_persistent_suspicious_clients(reputation)
            if persistent_suspicious:
                print(
                    f"  [HealthMonitor] Persistent suspicious clients detected: {persistent_suspicious} "
                    f"(DPS > {self.persistent_dps_threshold} for {self.persistent_rounds}+ consecutive rounds, "
                    f"trust <= {self.persistent_trust_threshold})"
                )
                return True

        # Check 4: Model drift
        if current_params is not None:
            drift = self.compute_model_drift(current_params)
            if drift is not None and drift > self.model_drift_threshold:
                print(
                    f"  [HealthMonitor] Model drift {drift:.3f} "
                    f"exceeds threshold {self.model_drift_threshold}"
                )
                return True

        return False

    def mark_as_trusted(self, params: List[np.ndarray]) -> None:
        """
        Mark current model parameters as trusted (for drift calculation).

        Args:
            params: Model parameters to mark as trusted
        """
        self.trusted_model_params = [p.copy() for p in params]

    def is_healthy(
        self,
        metrics: Dict[str, float],
        dps_dict: Optional[Dict[int, float]] = None,
        reputation: Optional[Dict[int, float]] = None,
    ) -> bool:
        """
        Check if current state is healthy (for checkpoint saving).

        Args:
            metrics: Current metrics
            dps_dict: Current DPS scores
            reputation: Client trust/reputation scores (optional)

        Returns:
            True if state is healthy
        """
        accuracy = metrics.get("accuracy", 0.0)
        loss = metrics.get("loss", float("inf"))

        # Must have minimum accuracy
        if accuracy < 0.5:  # Below random
            return False

        # Check DPS
        if dps_dict:
            avg_dps = np.mean(list(dps_dict.values()))
            if avg_dps > self.dps_threshold:
                return False

            # Persistent suspicious clients also indicate unhealthy state
            if self.get_persistent_suspicious_clients(reputation):
                return False

        # Check against baseline (if available)
        baseline_acc = self.get_baseline_accuracy()
        if baseline_acc is not None:
            if accuracy < baseline_acc - 0.05:  # Small tolerance
                return False

        return True

    def reset(self) -> None:
        """Reset all history (called after successful recovery)."""
        self.accuracy_history.clear()
        self.loss_history.clear()
        self.dps_history.clear()
        self.trusted_model_params = None
