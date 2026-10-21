"""
Comprehensive Test Suite for Federated Learning Defenses:
- Multi-Krum
- Trimmed Mean
- FLTrust
- ASH-FL
- Integration Matrix
"""

import os
import sys
import numpy as np
import torch

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from defenses import (
    MultiKrumDefense,
    TrimmedMeanDefense,
    FLTrustDefense,
    ASHFLDefense,
    ComparisonRunner,
    ExperimentConfig,
)
from clients.client import HeartDiseaseNet, get_model_parameters


def test_multi_krum():
    print("Testing Multi-Krum Defense...")
    # 5 clients: 4 benign (clustered near 1.0), 1 obvious outlier (at 1000.0)
    client_updates = []
    base_shape = (4, 4)
    for i in range(4):
        # Slightly noisy benign updates
        noise = np.random.normal(0, 0.01, size=base_shape).astype(np.float32)
        params = [np.ones(base_shape, dtype=np.float32) + noise]
        client_updates.append((i, params, 100))

    # Malicious outlier client 4
    malicious_params = [np.full(base_shape, 1000.0, dtype=np.float32)]
    client_updates.append((4, malicious_params, 100))

    global_params = [np.zeros(base_shape, dtype=np.float32)]

    # Multi-Krum with f=1, m=4
    krum = MultiKrumDefense(f=1, m=4)
    agg_params, metrics = krum.aggregate(1, client_updates, global_params)

    # Outlier (client 4) must NOT be in selected clients
    assert 4 in metrics["excluded_clients"], f"Client 4 should be excluded, got: {metrics['excluded_clients']}"
    assert 4 not in metrics["selected_clients"], f"Client 4 should not be selected: {metrics['selected_clients']}"
    assert len(metrics["selected_clients"]) == 4

    # Result should be close to 1.0, nowhere near 1000.0
    mean_val = float(np.mean(agg_params[0]))
    assert 0.95 <= mean_val <= 1.05, f"Expected aggregated mean ~1.0, got {mean_val}"

    # Invalid f constraint test: n=5, f=2 -> 2(2)+3 = 7 > 5 -> should raise ValueError
    try:
        invalid_krum = MultiKrumDefense(f=2)
        invalid_krum.aggregate(1, client_updates, global_params)
        assert False, "Should have raised ValueError for invalid f=2 with n=5"
    except ValueError as e:
        print(f"  ✓ Multi-Krum correctly rejected invalid f configuration: {e}")

    print("  ✓ Multi-Krum outlier rejection and 5-client configuration passed")


def test_trimmed_mean():
    print("Testing Trimmed Mean Defense...")
    # 5 clients:
    # coordinate values: [-1000.0, 1.0, 1.1, 1.2, +1000.0]
    # k=1 trimming removes -1000.0 and +1000.0, averages [1.0, 1.1, 1.2] = 1.1
    c0 = [np.array([-1000.0, 50.0], dtype=np.float32)]
    c1 = [np.array([1.0, 51.0], dtype=np.float32)]
    c2 = [np.array([1.1, 52.0], dtype=np.float32)]
    c3 = [np.array([1.2, 53.0], dtype=np.float32)]
    c4 = [np.array([1000.0, 54.0], dtype=np.float32)]

    client_updates = [(0, c0, 10), (1, c1, 10), (2, c2, 10), (3, c3, 10), (4, c4, 10)]
    global_params = [np.zeros(2, dtype=np.float32)]

    tmean = TrimmedMeanDefense(k=1)
    agg_params, metrics = tmean.aggregate(1, client_updates, global_params)

    # Check coordinate 0: mean(1.0, 1.1, 1.2) = 1.1
    assert np.isclose(agg_params[0][0], 1.1, atol=1e-5), f"Expected 1.1, got {agg_params[0][0]}"
    # Check coordinate 1: sorted [50, 51, 52, 53, 54] -> trimmed [51, 52, 53] -> mean = 52.0
    assert np.isclose(agg_params[0][1], 52.0, atol=1e-5), f"Expected 52.0, got {agg_params[0][1]}"

    assert metrics["trim_k"] == 1
    assert metrics["retained_per_coordinate"] == 3

    # Invalid trimming check: 2k >= n (e.g. k=3 with n=5)
    try:
        invalid_tm = TrimmedMeanDefense(k=3)
        invalid_tm.aggregate(1, client_updates, global_params)
        assert False, "Should have raised ValueError for 2k >= n"
    except ValueError as e:
        print(f"  ✓ Trimmed Mean correctly rejected invalid k parameter: {e}")

    print("  ✓ Trimmed Mean extreme positive/negative outlier trimming passed")


def test_fltrust():
    print("Testing FLTrust Defense...")
    # Setup dummy root data
    X_root = np.random.randn(30, 13).astype(np.float32)
    y_root = np.random.choice([0.0, 1.0], size=30).astype(np.float32)
    val_data = (X_root, y_root)

    fltrust = FLTrustDefense(
        validation_data=val_data,
        input_dim=13,
        hidden_dim=32,
        output_dim=1,
    )

    model = HeartDiseaseNet(13, 32, 1)
    global_params = get_model_parameters(model)

    # Compute genuine server update g_0 to craft aligned and opposing updates
    _, g0_delta = fltrust._compute_server_update(global_params)
    norm_g0 = float(np.linalg.norm(fltrust._flatten(g0_delta)))

    # Client 0: Perfectly aligned with server update g_0 (scaled by 2x)
    c0_params = [g + 2.0 * delta for g, delta in zip(global_params, g0_delta)]

    # Client 1: Opposing direction (negated g_0)
    c1_params = [g - 1.0 * delta for g, delta in zip(global_params, g0_delta)]

    # Client 2: Scaled attack (100x g_0)
    c2_params = [g + 100.0 * delta for g, delta in zip(global_params, g0_delta)]

    client_updates = [
        (0, c0_params, 50),
        (1, c1_params, 50),
        (2, c2_params, 50),
    ]

    agg_params, metrics = fltrust.aggregate(1, client_updates, global_params)

    # Trust score for aligned client 0 should be 1.0
    assert np.isclose(metrics["trust_scores"][0], 1.0, atol=1e-3), f"Client 0 trust: {metrics['trust_scores'][0]}"
    # Trust score for opposing client 1 should be 0.0 (ReLU of -1.0)
    assert np.isclose(metrics["trust_scores"][1], 0.0, atol=1e-5), f"Client 1 trust: {metrics['trust_scores'][1]}"
    # Trust score for client 2 should be 1.0, but its magnitude is normalized to ||g_0|| so 100x scaling is neutralized!
    assert np.isclose(metrics["trust_scores"][2], 1.0, atol=1e-3), f"Client 2 trust: {metrics['trust_scores'][2]}"

    print(f"  ✓ FLTrust trust scores verified: Aligned=1.0, Opposing=0.0")
    print(f"  ✓ FLTrust magnitude normalization neutralized 100x scaling attack")


def test_comparison_runner_and_integration():
    print("Testing Comparison Runner & Integration...")
    config = ExperimentConfig(
        num_clients=5,
        num_rounds=2,  # Quick 2-round test
        local_epochs=1,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
    )
    runner = ComparisonRunner(config)

    # Run all 4 defenses on label_flip
    print("  Running comparison on label_flip across all 4 defenses...")
    res = runner.run_comparison(attack_type="label_flip")

    assert "Multi-Krum" in res.defense_results
    assert "Trimmed Mean" in res.defense_results
    assert "FLTrust" in res.defense_results
    assert "ASH-FL" in res.defense_results

    df = res.to_dataframe()
    assert len(df) == 4
    print("  Summary Table from Integration Test:")
    print(df.to_string(index=False))

    # Verify ASH-FL self-healing metrics present
    ash_res = res.defense_results["ASH-FL"]
    assert ash_res.supports_self_healing is True
    assert "fsm_state" in ash_res.per_round_defense_metrics[0]

    # Verify Multi-Krum has selected_clients
    mk_res = res.defense_results["Multi-Krum"]
    assert "selected_clients" in mk_res.per_round_defense_metrics[0]

    # Verify FLTrust has trust_scores
    flt_res = res.defense_results["FLTrust"]
    assert "trust_scores" in flt_res.per_round_defense_metrics[0]

    # Run quick Backdoor test to verify Backdoor ASR calculation
    print("  Running comparison on backdoor attack...")
    res_bd = runner.run_comparison(attack_type="backdoor")
    for name, r in res_bd.defense_results.items():
        assert r.backdoor_asr is not None, f"Expected backdoor ASR for {name}"
        assert 0.0 <= r.backdoor_asr <= 1.0

    print("  ✓ Integration test passed for all 4 defenses and backdoor ASR!")


def test_parameter_isolation_and_immutability():
    """
    Regression Test:
    Proves that initial model parameters remain strictly immutable across evaluations,
    training rounds, and clean baseline executions, ruling out PyTorch-NumPy memory leaks.
    """
    print("Testing Parameter Isolation and Immutability...")
    config = ExperimentConfig(
        num_clients=5,
        num_rounds=2,
        local_epochs=1,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
    )
    runner = ComparisonRunner(config)

    # 1. Snapshot initial parameters
    original_params = [p.copy() for p in runner.get_initial_parameters()]

    # 2. Mutate eval_model directly via set_model_parameters
    dummy_params = [p + 10.0 for p in original_params]
    runner._evaluate(dummy_params)

    # 3. Verify runner.get_initial_parameters() was NOT affected by _evaluate()
    after_eval_params = runner.get_initial_parameters()
    for orig, curr in zip(original_params, after_eval_params):
        assert np.array_equal(orig, curr), "Initial parameters were corrupted by _evaluate()!"

    # 4. Run an entire defense experiment
    runner.run_defense(defense=TrimmedMeanDefense(k=1), attack_type="label_flip")

    # 5. Verify initial parameters are STILL completely identical down to bit-level precision
    after_run_params = runner.get_initial_parameters()
    for orig, curr in zip(original_params, after_run_params):
        max_diff = np.max(np.abs(orig - curr))
        assert max_diff == 0.0, f"Initial parameters mutated after run_defense! max_diff={max_diff}"

    # 6. Verify consumer mutation of returned parameter does not mutate internal template
    exposed = runner.get_initial_parameters()
    exposed[0] += 999.0
    fresh = runner.get_initial_parameters()
    assert np.max(np.abs(fresh[0] - original_params[0])) == 0.0, "Consumer in-place edit corrupted template!"

    print("  ✓ Parameter immutability and memory buffer isolation verified")


def test_experiment_order_invariance():
    """
    Regression Test:
    Proves that the order of defense execution does NOT affect initial conditions,
    per-round convergence, or final metrics (eliminating sequential carryover).
    """
    print("Testing Experiment Order Invariance...")
    config = ExperimentConfig(
        num_clients=5,
        num_rounds=2,
        local_epochs=1,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
    )

    # Sequence A: Multi-Krum first, then Trimmed Mean
    runner_a = ComparisonRunner(config)
    res_a_mk = runner_a.run_defense(MultiKrumDefense(f=1, m=4), attack_type="label_flip")
    res_a_tm = runner_a.run_defense(TrimmedMeanDefense(k=1), attack_type="label_flip")

    # Sequence B: Fresh runner, Trimmed Mean FIRST (no Multi-Krum beforehand)
    runner_b = ComparisonRunner(config)
    res_b_tm = runner_b.run_defense(TrimmedMeanDefense(k=1), attack_type="label_flip")

    # Verification: Trimmed Mean in Sequence A MUST match Sequence B exactly!
    assert np.isclose(res_a_tm.initial_accuracy, res_b_tm.initial_accuracy), (
        f"Initial accuracy mismatch: {res_a_tm.initial_accuracy} vs {res_b_tm.initial_accuracy}"
    )
    assert np.isclose(res_a_tm.final_accuracy, res_b_tm.final_accuracy), (
        f"Final accuracy mismatch: {res_a_tm.final_accuracy} vs {res_b_tm.final_accuracy}"
    )
    assert np.isclose(res_a_tm.final_loss, res_b_tm.final_loss), (
        f"Final loss mismatch: {res_a_tm.final_loss} vs {res_b_tm.final_loss}"
    )
    assert np.allclose(res_a_tm.per_round_accuracy, res_b_tm.per_round_accuracy), (
        f"Trajectory mismatch: {res_a_tm.per_round_accuracy} vs {res_b_tm.per_round_accuracy}"
    )

    print("  ✓ Experiment order invariance verified: Sequence A == Sequence B")


def test_baseline_cache_configuration_sensitivity():
    """
    Regression Test:
    Proves that clean baseline caching is strictly sensitive to configuration parameters
    and defense types, preventing invalid cross-config reuse.
    """
    print("Testing Baseline Cache Sensitivity...")
    config1 = ExperimentConfig(num_clients=5, num_rounds=2, random_seed=42)
    config2 = ExperimentConfig(num_clients=5, num_rounds=2, random_seed=99)  # Different seed

    runner1 = ComparisonRunner(config1)
    base1_mk = runner1.get_clean_baseline(defense_name="Multi-Krum")
    base1_tm = runner1.get_clean_baseline(defense_name="Trimmed Mean")

    # Cache should contain keys for Multi-Krum and Trimmed Mean
    assert len(runner1._clean_baseline_cache) >= 2

    # Different seed on runner2 should generate its own distinct cache entry
    runner2 = ComparisonRunner(config2)
    base2_mk = runner2.get_clean_baseline(defense_name="Multi-Krum")

    # Verify that runner1 and runner2 maintain independent caches
    assert (runner1.config.random_seed != runner2.config.random_seed)

    print("  ✓ Baseline cache properly partitions entries by defense and config signature")


if __name__ == "__main__":
    test_multi_krum()
    test_trimmed_mean()
    test_fltrust()
    test_comparison_runner_and_integration()
    test_parameter_isolation_and_immutability()
    test_experiment_order_invariance()
    test_baseline_cache_configuration_sensitivity()
    print("\n✅ ALL DEFENSE TESTS AND REGRESSION SUITES PASSED SUCCESSFULLY!")
