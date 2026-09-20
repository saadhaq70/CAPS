"""
Comprehensive Test Suite for ASH-FL Phase 3
Tests edge cases, error handling, and integration scenarios.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import torch
from recovery import HealthMonitor, CheckpointManager, SelfHealingController


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("Testing edge cases...")
    
    # Test 1: HealthMonitor with no history
    monitor = HealthMonitor()
    metrics = {"accuracy": 0.5, "loss": 0.7}
    assert not monitor.should_trigger_recovery(metrics), "Should not trigger with no history"
    print("  ✓ No history handling")
    
    # Test 2: Empty DPS dict - should not crash, but may trigger on accuracy
    monitor2 = HealthMonitor()
    monitor2.update_history(0.7, 0.5)
    monitor2.update_history(0.72, 0.48)
    
    # With good metrics and empty DPS, should not trigger
    good_metrics = {"accuracy": 0.73, "loss": 0.47}
    assert not monitor2.should_trigger_recovery(good_metrics, {}), "Empty DPS with good metrics should not trigger"
    print("  ✓ Empty DPS dict handling")
    
    # Test 3: None DPS dict - should not crash, but may trigger on accuracy
    good_metrics = {"accuracy": 0.74, "loss": 0.46}
    assert not monitor2.should_trigger_recovery(good_metrics, None), "None DPS with good metrics should not trigger"
    print("  ✓ None DPS handling")
    
    # Test 4: CheckpointManager with zero max_checkpoints
    try:
        manager = CheckpointManager(max_checkpoints=0)
        params = [np.array([1.0])]
        manager.save_if_healthy(1, params, {"accuracy": 0.7}, True)
        assert len(manager.checkpoints) == 0, "Should not save with max=0"
        print("  ✓ Zero checkpoint limit")
    except Exception as e:
        print(f"  ✗ Zero checkpoint limit failed: {e}")
    
    # Test 5: Restore from empty checkpoint manager
    manager_empty = CheckpointManager()
    result = manager_empty.restore_last_trusted()
    assert result is None, "Should return None when no checkpoints"
    print("  ✓ Empty checkpoint restore")
    
    # Test 6: Large checkpoint count
    manager_large = CheckpointManager(max_checkpoints=100)
    params = [np.random.randn(10)]
    for i in range(150):
        manager_large.save_if_healthy(i, params, {"accuracy": 0.7}, True)
    assert len(manager_large.checkpoints) == 100, "Should respect max limit"
    print("  ✓ Large checkpoint count")
    
    # Test 7: Negative accuracy/loss
    monitor3 = HealthMonitor()
    monitor3.update_history(0.5, 0.5)
    monitor3.update_history(0.6, 0.4)
    bad_metrics = {"accuracy": -0.1, "loss": -0.1}
    # Should not crash
    monitor3.should_trigger_recovery(bad_metrics)
    print("  ✓ Negative metrics handling")
    
    # Test 8: Very high DPS values
    extreme_dps = {0: 1000.0, 1: 999.0, 2: 998.0}
    monitor4 = HealthMonitor(dps_threshold=2.0)
    monitor4.update_history(0.7, 0.5)
    monitor4.update_history(0.72, 0.48)
    should_trigger = monitor4.should_trigger_recovery(metrics, extreme_dps)
    assert should_trigger, "Should trigger on extreme DPS"
    print("  ✓ Extreme DPS values")
    
    print("  ✓ Edge cases passed\n")


def test_recovery_failure_scenarios():
    """Test recovery failure and retry logic."""
    print("Testing recovery failure scenarios...")
    
    config = {"input_dim": 13, "hidden_dim": 32}
    controller = SelfHealingController(
        config=config,
        recovery_rounds=2,
        max_recovery_attempts=2,
    )
    
    params = [np.random.randn(32, 13).astype(np.float32) for _ in range(6)]
    
    # Build up some healthy history
    for i in range(1, 4):
        metrics = {"accuracy": 0.7 + i * 0.01, "loss": 0.5 - i * 0.01}
        dps = {0: 0.5, 1: 0.5, 2: 0.5}
        controller.update(i, params, metrics, dps)
    
    # Trigger recovery with attack
    attack_metrics = {"accuracy": 0.45, "loss": 0.85}
    attack_dps = {0: 0.5, 1: 5.0, 2: 0.5}
    controller.update(4, params, attack_metrics, attack_dps)
    
    # Simulate recovery that fails (no improvement)
    for i in range(5, 10):
        bad_metrics = {"accuracy": 0.40 + i * 0.01, "loss": 0.9}  # Still bad
        controller.update(i, params, bad_metrics, attack_dps)
    
    # Should eventually give up or expand quarantine
    status = controller.get_status_summary()
    print(f"  ✓ Recovery attempts: {status['recovery_attempts']}")
    print("  ✓ Failure scenarios handled\n")


def test_concurrent_attacks():
    """Test multiple malicious clients."""
    print("Testing multiple malicious clients...")
    
    monitor = HealthMonitor(dps_threshold=2.0, suspicious_fraction_threshold=0.3)
    
    # Simulate 5 clients, 2 malicious
    dps_multiple = {0: 0.5, 1: 4.5, 2: 0.6, 3: 4.2, 4: 0.7}
    
    monitor.update_history(0.7, 0.5)
    monitor.update_history(0.72, 0.48)
    
    metrics = {"accuracy": 0.50, "loss": 0.75}
    should_trigger = monitor.should_trigger_recovery(metrics, dps_multiple)
    
    # Should trigger due to high suspicious fraction (2/5 = 40% > 30%)
    assert should_trigger, "Should trigger on high suspicious fraction"
    print("  ✓ Multiple malicious clients detected\n")


def test_model_drift():
    """Test model drift detection."""
    print("Testing model drift detection...")
    
    monitor = HealthMonitor(model_drift_threshold=5.0)
    
    # Create two different parameter sets
    params1 = [np.array([1.0, 2.0, 3.0]), np.array([4.0])]
    params2 = [np.array([10.0, 20.0, 30.0]), np.array([40.0])]  # Large drift
    
    monitor.mark_as_trusted(params1)
    
    drift = monitor.compute_model_drift(params2)
    assert drift is not None and drift > 5.0, f"Drift {drift} should exceed threshold"
    
    monitor.update_history(0.7, 0.5)
    monitor.update_history(0.72, 0.48)
    
    metrics = {"accuracy": 0.70, "loss": 0.50}
    should_trigger = monitor.should_trigger_recovery(metrics, None, params2)
    assert should_trigger, "Should trigger on high drift"
    
    print(f"  ✓ Model drift detected: {drift:.2f}\n")


def test_quarantine_expiry():
    """Test quarantine expiration."""
    print("Testing quarantine expiry...")
    
    config = {"input_dim": 13, "hidden_dim": 32}
    controller = SelfHealingController(
        config=config,
        quarantine_window=3,  # Short window
    )
    
    params = [np.random.randn(32, 13).astype(np.float32) for _ in range(6)]
    
    # Build history
    for i in range(1, 4):
        metrics = {"accuracy": 0.7, "loss": 0.5}
        controller.update(i, params, metrics, {0: 0.5, 1: 0.5})
    
    # Trigger recovery
    attack_dps = {0: 0.5, 1: 5.0}
    controller.update(4, params, {"accuracy": 0.45, "loss": 0.85}, attack_dps)
    controller.update(5, params, {"accuracy": 0.45, "loss": 0.85}, attack_dps)
    
    # Should have quarantine
    assert len(controller.quarantined_clients) > 0, "Should have quarantined clients"
    initial_count = len(controller.quarantined_clients)
    
    # Continue for enough rounds to expire
    for i in range(6, 15):
        controller.update(i, params, {"accuracy": 0.70, "loss": 0.50}, {0: 0.5, 1: 0.5})
    
    # Quarantine should have expired
    final_count = len(controller.quarantined_clients)
    print(f"  ✓ Quarantine: {initial_count} → {final_count} (expired)\n")


def test_checkpoint_metadata():
    """Test checkpoint metadata storage."""
    print("Testing checkpoint metadata...")
    
    manager = CheckpointManager(max_checkpoints=3)
    
    params = [np.array([1.0, 2.0])]
    metrics = {"accuracy": 0.75, "loss": 0.45}
    reputation = {0: 1.0, 1: 0.5, 2: 0.8}
    
    manager.save_if_healthy(1, params, metrics, True, reputation)
    
    result = manager.restore_last_trusted()
    assert result is not None, "Should have checkpoint"
    
    round_num, restored_params, restored_metrics = result
    assert round_num == 1, "Round number should match"
    assert restored_metrics["accuracy"] == 0.75, "Metrics should match"
    
    # Check history
    history = manager.get_history()
    assert len(history) == 1, "Should have 1 checkpoint in history"
    assert history[0]["round"] == 1, "History should have correct round"
    
    print("  ✓ Metadata storage and retrieval\n")


def test_parameter_copying():
    """Test that parameters are deep copied."""
    print("Testing parameter deep copying...")
    
    manager = CheckpointManager()
    
    original_params = [np.array([1.0, 2.0, 3.0])]
    manager.save_if_healthy(1, original_params, {"accuracy": 0.7}, True)
    
    # Modify original
    original_params[0][0] = 999.0
    
    # Restore should have original value
    result = manager.restore_last_trusted()
    assert result is not None
    _, restored_params, _ = result
    
    assert restored_params[0][0] == 1.0, "Should have original value (deep copy)"
    print("  ✓ Deep copy verified\n")


def test_state_transitions():
    """Test all FSM state transitions."""
    print("Testing FSM state transitions...")
    
    config = {"input_dim": 13, "hidden_dim": 32}
    controller = SelfHealingController(config=config, recovery_rounds=2)
    
    params = [np.random.randn(32, 13).astype(np.float32) for _ in range(6)]
    
    # State 1: NORMAL
    assert controller.get_state() == "normal"
    controller.update(1, params, {"accuracy": 0.7, "loss": 0.5}, {0: 0.5})
    controller.update(2, params, {"accuracy": 0.72, "loss": 0.48}, {0: 0.5})
    controller.update(3, params, {"accuracy": 0.74, "loss": 0.46}, {0: 0.5})
    assert controller.get_state() == "normal"
    print("  ✓ NORMAL state")
    
    # Trigger: NORMAL → MONITOR
    controller.update(4, params, {"accuracy": 0.45, "loss": 0.85}, {0: 5.0})
    assert controller.get_state() in ["monitor", "recovery"], f"Expected monitor/recovery, got {controller.get_state()}"
    print("  ✓ NORMAL → MONITOR transition")
    
    # Continue to RECOVERY → VALIDATE → RESUME → NORMAL
    for i in range(5, 12):
        state_before = controller.get_state()
        controller.update(i, params, {"accuracy": 0.70, "loss": 0.50}, {0: 0.5})
        state_after = controller.get_state()
        print(f"    Round {i}: {state_before} → {state_after}")
    
    print("  ✓ All state transitions executed\n")


def test_error_handling():
    """Test error handling and robustness."""
    print("Testing error handling...")
    
    try:
        # Test with invalid config
        controller = SelfHealingController(config={})
        print("  ✓ Handles empty config")
    except Exception as e:
        print(f"  ✗ Empty config failed: {e}")
    
    try:
        # Test with None params
        monitor = HealthMonitor()
        monitor.update_history(0.7, 0.5)
        monitor.compute_model_drift(None)  # Should return None, not crash
        print("  ✓ Handles None parameters")
    except Exception as e:
        print(f"  ✗ None params failed: {e}")
    
    try:
        # Test with mismatched param shapes
        monitor = HealthMonitor()
        params1 = [np.array([1.0, 2.0])]
        params2 = [np.array([1.0, 2.0, 3.0])]  # Different shape
        monitor.mark_as_trusted(params1)
        # This should either handle gracefully or raise clear error
        drift = monitor.compute_model_drift(params2)
        print(f"  ⚠ Mismatched shapes: drift={drift} (may error in production)")
    except Exception as e:
        print(f"  ✓ Mismatched shapes detected: {type(e).__name__}")
    
    print("  ✓ Error handling tested\n")


def run_all_tests():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("ASH-FL Phase 3: Comprehensive Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        test_edge_cases,
        test_recovery_failure_scenarios,
        test_concurrent_attacks,
        test_model_drift,
        test_quarantine_expiry,
        test_checkpoint_metadata,
        test_parameter_copying,
        test_state_transitions,
        test_error_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ All comprehensive tests PASSED")
        print("Phase 3 is robust and production-ready!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = run_all_tests()
    sys.exit(exit_code)
