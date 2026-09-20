"""
ASH-FL Phase 2: Attack Demo
Runs a clean baseline and all four attack types back-to-back and prints
comparison metrics:
  - Label-flip / sign-flip / scaling : accuracy delta vs. clean baseline
  - Backdoor                         : clean accuracy + trigger Attack-Success-Rate

Usage:
    python attack_demo.py

The script is intentionally self-contained (no CLI args needed) and uses
the same minimal 3-client / 3-round configuration as demo_quick.py for speed.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import numpy as np

# ── Reproducibility ─────────────────────────────────────────────────────────
torch.manual_seed(42)
np.random.seed(42)

# ── Shared FL helpers ────────────────────────────────────────────────────────
import flwr as fl
from clients.data_loader import HeartDiseaseDataLoader
from clients.client import HeartDiseaseNet, get_model_parameters, set_model_parameters
from aggregation.strategy import FedAvgStrategy
from attacks.base import AttackConfig
from attacks.client_factory import get_client_fn_with_attacks
from attacks.backdoor import BackdoorAttack
from torch.utils.data import TensorDataset, DataLoader

# ── Demo hyper-parameters ────────────────────────────────────────────────────
NUM_CLIENTS = 5
NUM_ROUNDS  = 3      # keep fast; enough to see divergence
LOCAL_EP    = 3
BATCH_SZ    = 16
LR          = 0.01

BASE_CONFIG = {
    "input_dim":    13,
    "hidden_dim":   32,
    "output_dim":   1,
    "batch_size":   BATCH_SZ,
    "learning_rate": LR,
    "local_epochs": LOCAL_EP,
}

CLIENT_RESOURCES = {"num_cpus": 1, "num_gpus": 0.0}

SEPARATOR = "=" * 70


# ── Data loading (done once, reused across all runs) ─────────────────────────
print(SEPARATOR)
print("ASH-FL Phase 2: Attack Demo")
print(SEPARATOR)
print("\nLoading UCI Heart Disease dataset (shared across all runs)...")

loader = HeartDiseaseDataLoader(dataset_id=45, random_seed=42, test_split=0.2)
federated_data = loader.get_federated_data(num_clients=NUM_CLIENTS, iid=True)
client_data = federated_data["client_data"]
test_data   = federated_data["test_data"]
X_test, y_test = test_data
input_dim = federated_data["input_dim"]

# Update config with real input dim
BASE_CONFIG["input_dim"] = input_dim
print(f"  Dataset ready: {NUM_CLIENTS} clients, "
      f"test set = {len(X_test)} samples, "
      f"input_dim = {input_dim}")


# ── Helper: run one FL simulation ────────────────────────────────────────────
def run_simulation(attack_config: AttackConfig, label: str) -> float:
    """
    Run a single FL simulation and return final centralised test accuracy.

    Args:
        attack_config: AttackConfig to pass to the client factory.
        label:         Human-readable label for console output.

    Returns:
        Final round centralised test accuracy (float in [0, 1]).
    """
    print(f"\n{SEPARATOR}")
    print(f"  RUN: {label}")
    print(SEPARATOR)

    # Reset seeds so each run is comparable
    torch.manual_seed(42)
    np.random.seed(42)

    client_fn, ground_truth = get_client_fn_with_attacks(
        client_data=client_data,
        config=BASE_CONFIG,
        attack_config=attack_config,
    )

    strategy_wrapper = FedAvgStrategy(
        test_data=test_data,
        config=BASE_CONFIG,
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=NUM_CLIENTS,
        min_evaluate_clients=NUM_CLIENTS,
        min_available_clients=NUM_CLIENTS,
    )

    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=NUM_CLIENTS,
        config=fl.server.ServerConfig(num_rounds=NUM_ROUNDS),
        strategy=strategy_wrapper.get_strategy(),
        client_resources=CLIENT_RESOURCES,
    )

    if history.metrics_centralized and "accuracy" in history.metrics_centralized:
        accs = [a for _, a in history.metrics_centralized["accuracy"]]
        final_acc = accs[-1]
    else:
        final_acc = float("nan")

    print(f"\n  [{label}] Final accuracy: {final_acc:.4f}")
    return final_acc


# ── Helper: evaluate ASR for backdoor ────────────────────────────────────────
def evaluate_backdoor(history, attack_config: AttackConfig) -> tuple:
    """
    Evaluate the clean accuracy and Attack Success Rate (ASR) of the global
    model produced by a backdoor run.

    Args:
        history:       Flower History object from fl.simulation.start_simulation.
        attack_config: The backdoor AttackConfig used in the run.

    Returns:
        (clean_acc, asr) both in [0, 1].
    """
    # Reconstruct the global model from history is not directly available in
    # Flower's history; we evaluate on test data using stored centralized metrics
    # for clean accuracy, and re-create a poisoned test set for ASR.

    if history.metrics_centralized and "accuracy" in history.metrics_centralized:
        accs = [a for _, a in history.metrics_centralized["accuracy"]]
        clean_acc = accs[-1]
    else:
        clean_acc = float("nan")

    # For ASR we need to forward through the final global model.
    # The simplest way without modifying Flower internals is to stamp the
    # trigger on the test set and pass it through a model initialised to
    # the parameters that the strategy saw.  However, Flower does not expose
    # final parameters via History.
    #
    # Approach: we instantiate a fresh model, load the initial parameters,
    # then report that we cannot compute ASR from history alone.
    # In the attack_demo we use a proxy: run the global eval inside the
    # strategy's evaluate_fn after stamping the trigger on X_test.
    #
    # Since strategy.evaluate_fn is internal, we approximate ASR by
    # measuring what fraction of triggered test samples the model predicts
    # as backdoor_target_label — using the centralized accuracy as a proxy
    # for the final model quality and noting that stealthy backdoors keep
    # clean_acc ≈ baseline.  A proper ASR measurement would require access
    # to the aggregated weights; that plumbing is left for Phase 3.
    #
    # For the demo we return clean_acc and a sentinel so the display is clear.
    asr = float("nan")
    return clean_acc, asr


# ════════════════════════════════════════════════════════════════════════════
# 1. CLEAN BASELINE
# ════════════════════════════════════════════════════════════════════════════
baseline_cfg = AttackConfig(enabled=False)
baseline_acc = run_simulation(baseline_cfg, "CLEAN BASELINE (no attack)")


# ════════════════════════════════════════════════════════════════════════════
# 2. LABEL-FLIP ATTACK
# ════════════════════════════════════════════════════════════════════════════
lf_cfg = AttackConfig(
    enabled=True,
    attack_type="label_flip",
    num_malicious_clients=2,
    malicious_client_ids=[],
    source_label=0,
    target_label=1,
)
lf_acc = run_simulation(lf_cfg, "LABEL-FLIP ATTACK (2 clients, 0→1)")


# ════════════════════════════════════════════════════════════════════════════
# 3. SIGN-FLIP ATTACK
# ════════════════════════════════════════════════════════════════════════════
sf_cfg = AttackConfig(
    enabled=True,
    attack_type="sign_flip",
    num_malicious_clients=2,
    malicious_client_ids=[],
)
sf_acc = run_simulation(sf_cfg, "SIGN-FLIP ATTACK (2 clients)")


# ════════════════════════════════════════════════════════════════════════════
# 4. SCALING ATTACK
# ════════════════════════════════════════════════════════════════════════════
sc_cfg = AttackConfig(
    enabled=True,
    attack_type="scaling",
    num_malicious_clients=1,
    malicious_client_ids=[0],
    scale_factor=10.0,
)
sc_acc = run_simulation(sc_cfg, "SCALING ATTACK (1 client, 10x amplification)")


# ════════════════════════════════════════════════════════════════════════════
# 5. BACKDOOR ATTACK
# ════════════════════════════════════════════════════════════════════════════
bd_cfg = AttackConfig(
    enabled=True,
    attack_type="backdoor",
    num_malicious_clients=1,
    malicious_client_ids=[0],
    trigger_feature_indices=[0, 1],
    trigger_value=1.0,
    poison_fraction=0.3,
    backdoor_target_label=1,
)
bd_acc = run_simulation(bd_cfg, "BACKDOOR ATTACK (1 client, trigger on feat [0,1])")


# ════════════════════════════════════════════════════════════════════════════
# RESULTS SUMMARY
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{SEPARATOR}")
print("PHASE 2 ATTACK DEMO — RESULTS SUMMARY")
print(SEPARATOR)
print(f"{'Run':<40} {'Final Acc':>10} {'Δ vs Baseline':>14}")
print("-" * 66)

def _delta(acc: float) -> str:
    d = acc - baseline_acc
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:+.4f}"

rows = [
    ("Clean Baseline",                  baseline_acc),
    ("Label-Flip (2 clients, 0→1)",     lf_acc),
    ("Sign-Flip  (2 clients)",           sf_acc),
    ("Scaling   (1 client, 10x)",       sc_acc),
    ("Backdoor  (1 client, feat [0,1])", bd_acc),
]

for name, acc in rows:
    delta_str = "" if name == "Clean Baseline" else _delta(acc)
    print(f"  {name:<38} {acc:>10.4f} {delta_str:>14}")

print(SEPARATOR)
print("\nNotes:")
print("  • Label-flip / sign-flip / scaling should show accuracy DROPS.")
print("  • Backdoor should show accuracy CLOSE to baseline (stealthy).")
print("    Proper Attack-Success-Rate (ASR) measurement requires access to")
print("    the aggregated model weights — implemented in Phase 3 alongside DPS.")
print(f"\n{SEPARATOR}")
print("Phase 2 demo complete. Next: Phase 3 — DPS + robust aggregation.")
print(SEPARATOR)
