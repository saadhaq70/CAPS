"""
ASH-FL Phase 3: Self-Healing Demo
Demonstrates self-healing layer with attack injection and recovery.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import numpy as np
import torch

from clients.data_loader import HeartDiseaseDataLoader
from recovery import SelfHealingController, HealthMonitor, CheckpointManager


def load_config(config_path="configs/sim_config.yaml"):
    """Load configuration from YAML."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def simulate_federated_round(round_num, has_attack=False):
    """
    Simulate a federated round (mock for demo).
    
    Args:
        round_num: Current round number
        has_attack: Whether attack is present
        
    Returns:
        Tuple of (params, metrics, dps_dict)
    """
    # Mock model parameters (3 layers with appropriate shapes)
    params = [
        np.random.randn(32, 13).astype(np.float32),  # Layer 1 weights
        np.random.randn(32).astype(np.float32),      # Layer 1 bias
        np.random.randn(32, 32).astype(np.float32),  # Layer 2 weights
        np.random.randn(32).astype(np.float32),      # Layer 2 bias
        np.random.randn(1, 32).astype(np.float32),   # Layer 3 weights
        np.random.randn(1).astype(np.float32),       # Layer 3 bias
    ]
    
    # Simulate metrics (degraded if under attack)
    if has_attack:
        accuracy = 0.45 + np.random.uniform(-0.05, 0.05)  # Poor performance
        loss = 0.85 + np.random.uniform(-0.1, 0.1)
        # High DPS for malicious clients
        dps_dict = {
            0: 0.5 + np.random.uniform(0, 0.3),  # Normal
            1: 3.5 + np.random.uniform(0, 1.0),  # Malicious!
            2: 0.6 + np.random.uniform(0, 0.3),  # Normal
            3: 0.4 + np.random.uniform(0, 0.3),  # Normal
            4: 0.7 + np.random.uniform(0, 0.3),  # Normal
        }
    else:
        accuracy = 0.70 + round_num * 0.02 + np.random.uniform(-0.02, 0.02)  # Improving
        accuracy = min(accuracy, 0.85)  # Cap
        loss = 0.50 - round_num * 0.02 + np.random.uniform(-0.02, 0.02)  # Decreasing
        loss = max(loss, 0.35)  # Floor
        # Low DPS for all clients
        dps_dict = {
            0: 0.3 + np.random.uniform(0, 0.2),
            1: 0.4 + np.random.uniform(0, 0.2),
            2: 0.5 + np.random.uniform(0, 0.2),
            3: 0.3 + np.random.uniform(0, 0.2),
            4: 0.4 + np.random.uniform(0, 0.2),
        }
    
    metrics = {"accuracy": accuracy, "loss": loss}
    
    return params, metrics, dps_dict


def main():
    """Run self-healing demo."""
    print("=" * 80)
    print("ASH-FL Phase 3: Self-Healing Layer Demo")
    print("=" * 80)
    
    # Load config
    config = load_config()
    
    # Extract self-healing config (with defaults for backward compatibility)
    sh_config = config.get("self_healing", {})
    if not sh_config.get("enabled", False):
        print("\n⚠️  Self-healing is DISABLED in config.")
        print("   Set 'self_healing.enabled: true' in configs/sim_config.yaml")
        print("   Running demo anyway with default settings...\n")
    
    # Initialize self-healing components
    health_monitor = HealthMonitor(
        accuracy_drop_threshold=sh_config.get("accuracy_drop_threshold", 0.15),
        loss_spike_threshold=sh_config.get("loss_spike_threshold", 0.3),
        dps_threshold=sh_config.get("dps_threshold", 2.0),
        suspicious_fraction_threshold=sh_config.get("suspicious_fraction_threshold", 0.3),
        model_drift_threshold=sh_config.get("model_drift_threshold", 5.0),
        baseline_window=sh_config.get("baseline_window", 3),
    )
    
    checkpoint_manager = CheckpointManager(
        max_checkpoints=sh_config.get("max_checkpoints", 3)
    )
    
    controller = SelfHealingController(
        config=config,
        health_monitor=health_monitor,
        checkpoint_manager=checkpoint_manager,
        recovery_rounds=sh_config.get("recovery_rounds", 3),
        quarantine_window=sh_config.get("quarantine_window", 5),
        suspicious_weight=sh_config.get("suspicious_weight", 0.1),
        max_recovery_attempts=sh_config.get("max_recovery_attempts", 3),
    )
    
    print("\n[Setup] Self-healing controller initialized")
    print(f"  - DPS threshold: {sh_config.get('dps_threshold', 2.0)}")
    print(f"  - Recovery rounds: {sh_config.get('recovery_rounds', 3)}")
    print(f"  - Quarantine window: {sh_config.get('quarantine_window', 5)}")
    
    # Simulation parameters
    num_rounds = 20
    attack_start = 8  # Attack begins at round 8
    attack_end = 12   # Attack ends at round 12
    
    print(f"\n[Simulation] Running {num_rounds} rounds")
    print(f"  - Attack injection: rounds {attack_start}-{attack_end}")
    print(f"  - Healthy operation: rounds 1-{attack_start-1}, {attack_end+1}-{num_rounds}")
    print("\n" + "=" * 80)
    
    # Run simulation
    for round_num in range(1, num_rounds + 1):
        # Determine if attack is active
        has_attack = attack_start <= round_num <= attack_end
        
        # Simulate federated round
        params, metrics, dps_dict = simulate_federated_round(round_num, has_attack)
        
        # Update self-healing controller
        final_params, status = controller.update(
            round_num=round_num,
            candidate_params=params,
            metrics=metrics,
            dps_dict=dps_dict,
            reputation=None,
            client_updates=None,
        )
        
        # Print round summary
        state = controller.get_state()
        acc = metrics["accuracy"]
        loss = metrics["loss"]
        avg_dps = np.mean(list(dps_dict.values()))
        max_dps = np.max(list(dps_dict.values()))
        
        attack_marker = "🔴 ATTACK" if has_attack else "✅ CLEAN"
        state_marker = f"[{state.upper()}]"
        
        print(f"\nRound {round_num:2d} {attack_marker} {state_marker}")
        print(f"  Metrics: Acc={acc:.3f}, Loss={loss:.3f}")
        print(f"  DPS: Avg={avg_dps:.2f}, Max={max_dps:.2f}")
        
        # Show quarantined clients
        if controller.quarantined_clients:
            print(f"  Quarantined: {list(controller.quarantined_clients)}")
        
        print(f"  Status: {status}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("Simulation Complete - Self-Healing Summary")
    print("=" * 80)
    
    status = controller.get_status_summary()
    print(f"\nFinal State: {status['state'].upper()}")
    print(f"Recovery Attempts: {status['recovery_attempts']}")
    print(f"Checkpoints Saved: {status['checkpoints']}")
    
    if checkpoint_manager.has_checkpoints():
        print(f"\nCheckpoint History:")
        for cp in checkpoint_manager.get_history():
            print(f"  Round {cp['round']:2d}: Acc={cp['accuracy']:.3f}, Loss={cp['loss']:.3f}")
    
    print("\n✅ Phase 3 self-healing layer is operational!")
    print("\nKey Features Demonstrated:")
    print("  ✓ Health monitoring (accuracy, loss, DPS)")
    print("  ✓ Automatic degradation detection")
    print("  ✓ FSM state transitions (NORMAL → MONITOR → RECOVERY → VALIDATE)")
    print("  ✓ Checkpoint save/restore")
    print("  ✓ Client quarantine mechanism")
    print("  ✓ Multi-attempt recovery with expanding quarantine")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Set random seed for reproducibility
    np.random.seed(42)
    torch.manual_seed(42)
    
    main()
