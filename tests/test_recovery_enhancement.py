"""
Unit tests for ASH-FL Option C persistent malicious-client detection and recovery lifecycle.
"""

import pytest
import numpy as np

from recovery import HealthMonitor, CheckpointManager, SelfHealingController
from recovery.self_heal import HealingState


def _make_mock_params(dim: int = 10) -> list:
    """Generate mock model parameters for testing."""
    return [
        np.ones((dim, dim), dtype=np.float32) * 0.5,
        np.zeros((dim,), dtype=np.float32),
    ]


def test_persistent_suspicious_dps_with_declining_trust_triggers_recovery_and_quarantine():
    """
    Scenario 1:
    Persistent suspicious DPS (> 0.45 for >= 2 consecutive rounds) + declining trust (<= 0.85)
    triggers recovery confirmation and client quarantine, even when DPS is below 0.55.
    """
    monitor = HealthMonitor(
        dps_threshold=0.55,
        persistent_dps_threshold=0.45,
        persistent_trust_threshold=0.85,
        persistent_rounds=2,
    )
    checkpoint_mgr = CheckpointManager()
    controller = SelfHealingController(
        config={},
        health_monitor=monitor,
        checkpoint_manager=checkpoint_mgr,
        quarantine_window=3,
        recovery_rounds=2,
    )

    params = _make_mock_params()

    # Round 1: Healthy operation (establishes baseline)
    metrics_r1 = {"accuracy": 0.75, "loss": 0.50}
    dps_r1 = {0: 0.12, 1: 0.14, 2: 0.11}
    trust_r1 = {0: 1.0, 1: 1.0, 2: 1.0}
    p, status = controller.update(1, params, metrics_r1, dps_r1, trust_r1)
    assert controller.get_state() == "normal"
    assert len(checkpoint_mgr.checkpoints) == 1

    # Round 2: Client 1 first suspicious round (DPS=0.50 > 0.45, but <= 0.55; trust=0.90 > 0.85)
    # Only 1 round of elevated DPS, and trust still > 0.85 -> should stay NORMAL
    metrics_r2 = {"accuracy": 0.74, "loss": 0.51}
    dps_r2 = {0: 0.12, 1: 0.50, 2: 0.11}
    trust_r2 = {0: 0.99, 1: 0.90, 2: 0.99}
    p, status = controller.update(2, params, metrics_r2, dps_r2, trust_r2)
    assert controller.get_state() == "normal", "Single round below 0.55 should not trigger alert"
    assert not controller.is_client_quarantined(1)

    # Round 3: Client 1 second consecutive suspicious round (DPS=0.49 > 0.45, trust decayed to 0.82 <= 0.85)
    # Now BOTH conditions are satisfied: consecutive rounds >= 2 AND trust <= 0.85
    # Should detect degradation and enter MONITOR
    metrics_r3 = {"accuracy": 0.73, "loss": 0.52}
    dps_r3 = {0: 0.12, 1: 0.49, 2: 0.11}
    trust_r3 = {0: 0.98, 1: 0.82, 2: 0.98}
    p, status = controller.update(3, params, metrics_r3, dps_r3, trust_r3)
    assert controller.get_state() == "monitor", f"Expected monitor, got {controller.get_state()}"

    # Round 4: Persistent degradation confirmed in MONITOR -> transitions to RECOVERY
    metrics_r4 = {"accuracy": 0.72, "loss": 0.53}
    dps_r4 = {0: 0.11, 1: 0.48, 2: 0.10}
    trust_r4 = {0: 0.97, 1: 0.78, 2: 0.97}
    p, status = controller.update(4, params, metrics_r4, dps_r4, trust_r4)
    assert controller.get_state() == "recovery", f"Expected recovery, got {controller.get_state()}"

    # Verify Client 1 is quarantined and penalized
    assert controller.is_client_quarantined(1), "Client 1 should be quarantined"
    assert controller.get_client_weight_multiplier(1) == 0.1
    # Benign clients should not be quarantined
    assert not controller.is_client_quarantined(0)
    assert controller.get_client_weight_multiplier(0) == 1.0


def test_consecutive_benign_dps_spikes_with_healthy_trust_do_not_trigger_recovery():
    """
    Scenario 2:
    Consecutive moderate DPS spikes (e.g. 0.47, 0.48) with healthy trust (> 0.85)
    do not trigger recovery or quarantine.
    """
    monitor = HealthMonitor(
        dps_threshold=0.55,
        persistent_dps_threshold=0.45,
        persistent_trust_threshold=0.85,
        persistent_rounds=2,
    )
    controller = SelfHealingController(config={}, health_monitor=monitor)
    params = _make_mock_params()

    # Round 1: Normal
    controller.update(1, params, {"accuracy": 0.75, "loss": 0.50}, {0: 0.10, 1: 0.10}, {0: 1.0, 1: 1.0})

    # Round 2: Spike 1 (DPS=0.47), but healthy trust = 0.95
    controller.update(2, params, {"accuracy": 0.76, "loss": 0.49}, {0: 0.10, 1: 0.47}, {0: 1.0, 1: 0.95})
    assert controller.get_state() == "normal"

    # Round 3: Spike 2 (DPS=0.48), consecutive, but healthy trust = 0.92 (> 0.85)
    controller.update(3, params, {"accuracy": 0.77, "loss": 0.48}, {0: 0.10, 1: 0.48}, {0: 1.0, 1: 0.92})
    assert controller.get_state() == "normal", "Healthy trust should veto persistent alert"
    assert not controller.is_client_quarantined(1)


def test_non_consecutive_dps_spikes_do_not_trigger_persistent_recovery():
    """
    Scenario 3:
    Non-consecutive DPS spikes do not satisfy the consecutive rounds requirement
    and do not trigger persistent recovery.
    """
    monitor = HealthMonitor(
        dps_threshold=0.55,
        persistent_dps_threshold=0.45,
        persistent_trust_threshold=0.85,
        persistent_rounds=2,
    )
    controller = SelfHealingController(config={}, health_monitor=monitor)
    params = _make_mock_params()

    # Round 1: Healthy
    controller.update(1, params, {"accuracy": 0.75, "loss": 0.50}, {0: 0.10, 1: 0.10}, {0: 1.0, 1: 1.0})

    # Round 2: First spike (DPS=0.48), trust=0.80
    controller.update(2, params, {"accuracy": 0.75, "loss": 0.50}, {0: 0.10, 1: 0.48}, {0: 1.0, 1: 0.80})
    assert controller.get_state() == "normal"

    # Round 3: Recovers to benign DPS (0.20), breaking consecutive streak
    controller.update(3, params, {"accuracy": 0.76, "loss": 0.49}, {0: 0.10, 1: 0.20}, {0: 1.0, 1: 0.80})
    assert controller.get_state() == "normal"

    # Round 4: Isolated spike (DPS=0.48). Last 2 rounds are [0.20, 0.48] -> not consecutive!
    controller.update(4, params, {"accuracy": 0.76, "loss": 0.49}, {0: 0.10, 1: 0.48}, {0: 1.0, 1: 0.80})
    assert controller.get_state() == "normal", "Non-consecutive spike must not trigger persistent recovery"
    assert not controller.is_client_quarantined(1)


def test_acute_scaling_attack_triggers_immediate_recovery_on_first_spike():
    """
    Scenario 4:
    Acute scaling attack with high DPS (> 0.55) triggers immediate alert on the very first spike,
    without requiring consecutive rounds or trust decay.
    """
    monitor = HealthMonitor(
        dps_threshold=0.55,
        persistent_dps_threshold=0.45,
        persistent_trust_threshold=0.85,
        persistent_rounds=2,
    )
    controller = SelfHealingController(config={}, health_monitor=monitor)
    params = _make_mock_params()

    # Round 1: Baseline
    controller.update(1, params, {"accuracy": 0.75, "loss": 0.50}, {0: 0.10, 1: 0.10}, {0: 1.0, 1: 1.0})

    # Round 2: Massive acute gradient scaling attack (DPS=0.999), trust is fresh (1.0)
    # Must immediately trigger alert on round 2
    metrics_r2 = {"accuracy": 0.74, "loss": 0.52}
    dps_r2 = {0: 0.10, 1: 0.999}
    trust_r2 = {0: 1.0, 1: 1.0}

    # Verify HealthMonitor check directly
    assert monitor.should_trigger_recovery(metrics_r2, dps_r2, reputation=trust_r2) is True

    # Verify FSM transition on first spike
    p, status = controller.update(2, params, metrics_r2, dps_r2, trust_r2)
    assert controller.get_state() in ["monitor", "recovery"], "Acute attack must immediately trigger alert"


def test_transient_false_alarm_resolves_to_normal():
    """
    Scenario 5:
    A transient DPS spike that triggers MONITOR but normalizes on the next round
    correctly resolves as a false alarm and returns to NORMAL without quarantine or rollback.
    """
    monitor = HealthMonitor(dps_threshold=0.55)
    controller = SelfHealingController(config={}, health_monitor=monitor)
    params = _make_mock_params()

    # Round 1: Normal
    controller.update(1, params, {"accuracy": 0.80, "loss": 0.40}, {0: 0.10, 1: 0.10})
    assert controller.get_state() == "normal"

    # Round 2: Transient spike (DPS=0.58 > 0.55) -> enters MONITOR
    controller.update(2, params, {"accuracy": 0.79, "loss": 0.41}, {0: 0.10, 1: 0.58})
    assert controller.get_state() == "monitor"

    # Round 3: Metric normalizes completely (DPS=0.15, accuracy=0.82)
    p, status = controller.update(3, params, {"accuracy": 0.82, "loss": 0.38}, {0: 0.10, 1: 0.15})
    assert controller.get_state() == "normal", "Transient noise should resolve to NORMAL"
    assert "False alarm" in status or "resolved" in status
    assert len(controller.quarantined_clients) == 0


def test_clean_training_across_five_rounds_maintains_normal():
    """
    Scenario 6:
    Clean federated training across 5 rounds maintains NORMAL state throughout,
    with zero quarantines and zero recovery attempts.
    """
    controller = SelfHealingController(config={}, recovery_rounds=2)
    params = _make_mock_params()

    accuracies = [0.70, 0.73, 0.76, 0.79, 0.82]
    losses = [0.60, 0.55, 0.50, 0.45, 0.40]

    for round_num in range(1, 6):
        acc = accuracies[round_num - 1]
        loss = losses[round_num - 1]
        metrics = {"accuracy": acc, "loss": loss}
        dps = {cid: 0.10 + 0.02 * cid for cid in range(5)}
        trust = {cid: 1.0 for cid in range(5)}

        p, status = controller.update(round_num, params, metrics, dps, trust)

        assert controller.get_state() == "normal", f"Round {round_num} should remain NORMAL"
        assert len(controller.quarantined_clients) == 0, f"Round {round_num} should have 0 quarantined clients"
        assert controller.recovery_attempt_count == 0, f"Round {round_num} should have 0 recovery attempts"

    summary = controller.get_status_summary()
    assert summary["state"] == "normal"
    assert summary["quarantined_clients"] == []
    assert summary["recovery_attempts"] == 0


def test_full_recovery_lifecycle_success_and_failure():
    """
    Scenario 7:
    Full recovery lifecycle:
    Part A: Degradation confirmation -> Checkpoint restore -> Retraining -> Validation success -> Resume -> Normal.
    Part B: Validation failure -> Quarantine expansion -> Retry.
    """
    # ── PART A: Successful recovery lifecycle ──
    controller = SelfHealingController(
        config={},
        recovery_rounds=2,
        quarantine_window=3,
        suspicious_weight=0.1,
    )
    trusted_params = _make_mock_params()
    poisoned_params = [p + 5.0 for p in trusted_params]

    # Round 1: Healthy (saves checkpoint)
    controller.update(1, trusted_params, {"accuracy": 0.80, "loss": 0.40}, {0: 0.1, 1: 0.1})
    assert controller.get_state() == "normal"

    # Round 2: Healthy progress
    controller.update(2, trusted_params, {"accuracy": 0.82, "loss": 0.38}, {0: 0.1, 1: 0.1})
    assert controller.get_state() == "normal"

    # Round 3: Attack detected -> MONITOR
    attack_dps = {0: 0.1, 1: 0.90}
    controller.update(3, poisoned_params, {"accuracy": 0.50, "loss": 0.80}, attack_dps)
    assert controller.get_state() == "monitor"

    # Round 4: Degradation confirmed -> RECOVERY (checkpoint restored, client 1 quarantined)
    restored_p, status = controller.update(4, poisoned_params, {"accuracy": 0.48, "loss": 0.85}, attack_dps)
    assert controller.get_state() == "recovery"
    assert controller.is_client_quarantined(1)
    # Restored params should match trusted checkpoint
    np.testing.assert_array_almost_equal(restored_p[0], trusted_params[0])

    # Round 5: First recovery retraining round (rounds_in_recovery = 5 - 4 = 1 < 2)
    controller.update(5, restored_p, {"accuracy": 0.70, "loss": 0.55}, attack_dps)
    assert controller.get_state() == "recovery"
    assert controller.is_client_quarantined(1)

    # Round 6: Recovery retraining complete (rounds_in_recovery = 6 - 4 = 2 >= 2) -> VALIDATE
    controller.update(6, restored_p, {"accuracy": 0.78, "loss": 0.45}, attack_dps)
    assert controller.get_state() == "validate"

    # Round 7: Validation check - accuracy improved from pre-recovery (0.48 -> 0.83) -> RESUME
    controller.update(7, restored_p, {"accuracy": 0.83, "loss": 0.39}, attack_dps)
    assert controller.get_state() == "resume"

    # Round 8: Resume transitions back to NORMAL
    controller.update(8, restored_p, {"accuracy": 0.84, "loss": 0.38}, {0: 0.1, 1: 0.1})
    assert controller.get_state() == "normal"

    # ── PART B: Failed recovery triggers quarantine expansion ──
    controller_fail = SelfHealingController(
        config={},
        recovery_rounds=1,
        max_recovery_attempts=3,
    )
    # Healthy baseline
    controller_fail.update(1, trusted_params, {"accuracy": 0.80, "loss": 0.40}, {0: 0.1, 1: 0.1, 2: 0.1})
    controller_fail.update(2, trusted_params, {"accuracy": 0.82, "loss": 0.38}, {0: 0.1, 1: 0.1, 2: 0.1})

    # Trigger attack & recovery
    attack_dps_multi = {0: 0.1, 1: 0.90, 2: 0.40}
    controller_fail.update(3, poisoned_params, {"accuracy": 0.50, "loss": 0.80}, attack_dps_multi)
    controller_fail.update(4, poisoned_params, {"accuracy": 0.48, "loss": 0.85}, attack_dps_multi)
    assert controller_fail.get_state() == "recovery"

    # Complete recovery retraining -> enter VALIDATE
    controller_fail.update(5, poisoned_params, {"accuracy": 0.47, "loss": 0.88}, attack_dps_multi)
    assert controller_fail.get_state() == "validate"

    # Validation round: accuracy did not improve (0.47 vs pre_acc 0.48) -> recovery FAILS
    # Quarantine should expand and FSM returns to RECOVERY (attempt 2)
    controller_fail.update(6, poisoned_params, {"accuracy": 0.47, "loss": 0.88}, attack_dps_multi)
    assert controller_fail.get_state() == "recovery"
    assert controller_fail.recovery_attempt_count == 2
    # Client 2 (DPS 0.40 > threshold * 0.7 = 0.55 * 0.7 = 0.385) should be added to expanded quarantine
    assert controller_fail.is_client_quarantined(2)
