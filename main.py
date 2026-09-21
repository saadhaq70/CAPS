"""
ASH-FL: Federated Learning Simulator
Main entry point for running FL simulation with FedAvg baseline.
Phase 1: clean baseline.  Phase 2: attack harness (set attack.enabled: true).
"""

import yaml
import flwr as fl
import torch
import numpy as np
from pathlib import Path

from clients.data_loader import HeartDiseaseDataLoader
from clients.client import get_client_fn, HeartDiseaseNet, get_model_parameters
from aggregation.strategy import FedAvgStrategy, AdaptiveStrategy
from attacks.base import AttackConfig
from attacks.client_factory import get_client_fn_with_attacks


def load_config(config_path: str = "configs/sim_config.yaml") -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def initialize_global_model(config: dict) -> list:
    """
    Initialize global model parameters.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of initial model parameters
    """
    model = HeartDiseaseNet(
        input_dim=config["input_dim"],
        hidden_dim=config["hidden_dim"],
        output_dim=config["output_dim"]
    )
    return get_model_parameters(model)


def main():
    """Main function to run federated learning simulation."""

    print("=" * 80)
    print("ASH-FL: Federated Learning Simulator")
    print("=" * 80)
    
    # Load configuration
    print("\n[1/5] Loading configuration...")
    config = load_config()
    print(f"  - Simulation Rounds: {config['num_rounds']}")
    print(f"  - Total Clients: {config['num_clients_total']}")
    print(f"  - Clients per Round: {config['num_clients_per_round']}")
    print(f"  - Strategy: {config['strategy']}")
    print(f"  - Learning Rate: {config['learning_rate']}")
    print(f"  - Local Epochs: {config['local_epochs']}")

    # Parse attack config (Phase 2 addition; safe when attack.enabled = false)
    attack_cfg_raw = config.get("attack", {})
    attack_config = AttackConfig.from_dict(attack_cfg_raw)
    if attack_config.enabled:
        print(f"  - Attack: {attack_config.attack_type.upper()} "
              f"({attack_config.num_malicious_clients} malicious client(s))")
    else:
        print("  - Attack: disabled (clean Phase 1 baseline)")
    
    # Parse self-healing config (Phase 3 addition; safe when self_healing.enabled = false)
    self_healing_cfg = config.get("self_healing", {})
    self_healing_enabled = self_healing_cfg.get("enabled", False)
    if self_healing_enabled:
        print(f"  - Self-Healing: ENABLED")
        print(f"    - DPS Threshold: {self_healing_cfg.get('dps_threshold', 0.55)}")
        print(f"    - Recovery Rounds: {self_healing_cfg.get('recovery_rounds', 3)}")
    else:
        print("  - Self-Healing: disabled")
    
    # Load and partition dataset
    print("\n[2/5] Loading and partitioning UCI Heart Disease dataset...")
    data_loader = HeartDiseaseDataLoader(
        dataset_id=config["dataset_id"],
        random_seed=config["random_seed"],
        test_split=config["test_split"]
    )
    
    federated_data = data_loader.get_federated_data(
        num_clients=config["num_clients_total"],
        iid=config["iid"]
    )
    
    client_datasets = federated_data["client_data"]
    test_data = federated_data["test_data"]
    
    # Update config with actual input dimension
    config["input_dim"] = federated_data["input_dim"]
    print(f"  - Input Dimension: {config['input_dim']}")
    print(f"  - Test Set Size: {len(test_data[0])} samples")
    
    # Initialize global model
    print("\n[3/5] Initializing global model...")
    initial_parameters = initialize_global_model(config)
    print(f"  - Model: HeartDiseaseNet (3-layer MLP)")
    print(f"  - Parameters: {sum(p.size for p in initial_parameters)} weights")
    print(f"  - Device: {'GPU' if torch.cuda.is_available() else 'CPU'}")
    
    # Create client factory function (Phase 2: attack-aware)
    print("\n[4/5] Setting up federated clients...")
    client_fn, ground_truth = get_client_fn_with_attacks(
        client_data=client_datasets,
        config=config,
        attack_config=attack_config,
    )
    print(f"  - Client spawning function created")
    print(f"  - Each client will train for {config['local_epochs']} local epochs per round")
    if attack_config.enabled:
        mal_ids = [cid for cid, bad in ground_truth.items() if bad]
        print(f"  - Ground-truth malicious IDs (for Phase 3 scoring): {mal_ids}")
    
    # Configure aggregation strategy (adaptive when self-healing enabled, FedAvg otherwise)
    print("\n[5/5] Configuring aggregation strategy...")
    
    if self_healing_enabled:
        # Use AdaptiveStrategy with DPS-based trust and quarantine
        print(f"  - Strategy: AdaptiveStrategy (DPS-aware with self-healing)")
        strategy_wrapper = AdaptiveStrategy(
            test_data=test_data,
            config=config,
            fraction_fit=config["fraction_fit"],
            fraction_evaluate=config["fraction_evaluate"],
            min_fit_clients=config["min_fit_clients"],
            min_evaluate_clients=config["min_evaluate_clients"],
            min_available_clients=config["min_available_clients"],
            self_healing_enabled=True
        )
        strategy = strategy_wrapper
        
        # NOTE: For full self-healing integration, you would need to:
        # 1. Import HealthMonitor and SelfHealingController
        # 2. Initialize DPS calculator with validation data
        # 3. Hook into aggregate_fit to update client scores each round
        # 4. This requires custom Flower server implementation
        #
        # For now, AdaptiveStrategy is ready but requires external score updates
        # (as demonstrated in unified_dashboard.py via DashboardSimulator)
        
        print(f"  - Note: Full CLI self-healing integration requires custom Flower server")
        print(f"  - Use unified_dashboard.py for complete self-healing demonstration")
    else:
        # Use plain FedAvg (Phase 1/2 behavior)
        print(f"  - Strategy: FedAvg (non-robust baseline)")
        strategy_wrapper = FedAvgStrategy(
            test_data=test_data,
            config=config,
            fraction_fit=config["fraction_fit"],
            fraction_evaluate=config["fraction_evaluate"],
            min_fit_clients=config["min_fit_clients"],
            min_evaluate_clients=config["min_evaluate_clients"],
            min_available_clients=config["min_available_clients"]
        )
        strategy = strategy_wrapper.get_strategy()
    
    print(f"  - Server-side evaluation enabled on global test set")
    
    # Start federated learning simulation
    print("\n" + "=" * 80)
    print("Starting Federated Learning Simulation")
    print("=" * 80)
    print("\nNote: Server only receives model weights/deltas, never raw data.\n")
    
    # Configure simulation
    client_resources = {
        "num_cpus": 1,
        "num_gpus": 0.0  # Set to fractional value if GPUs available
    }
    
    # Run simulation
    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=config["num_clients_total"],
        config=fl.server.ServerConfig(num_rounds=config["num_rounds"]),
        strategy=strategy,
        client_resources=client_resources,
    )
    
    # Print final results
    print("\n" + "=" * 80)
    print("Simulation Complete - Final Results")
    print("=" * 80)
    
    if history.metrics_centralized:
        final_round = config["num_rounds"]
        if "accuracy" in history.metrics_centralized:
            accuracies = [acc for _, acc in history.metrics_centralized["accuracy"]]
            print(f"\nGlobal Model Performance (Centralized Test Set):")
            print(f"  - Initial Accuracy: {accuracies[0]:.4f}")
            print(f"  - Final Accuracy: {accuracies[-1]:.4f}")
            print(f"  - Improvement: {(accuracies[-1] - accuracies[0]):.4f}")
            
            print(f"\nAccuracy per Round:")
            for round_num, acc in enumerate(accuracies, 1):
                print(f"  Round {round_num}: {acc:.4f}")
    
    print("\n" + "=" * 80)
    if self_healing_enabled:
        print("Phase 3 Complete: Self-healing FL simulation with AdaptiveStrategy")
        print("Note: For full self-healing with DPS detection, use:")
        print("  bash run_unified.sh")
    elif attack_config.enabled:
        print(f"Phase 2 Complete: Attack simulation [{attack_config.attack_type}] done.")
    else:
        print("Phase 1/2 Complete: Baseline FL simulation successful!")
    print("Next Steps:")
    print("  - Run 'bash run_unified.sh' for complete self-healing demo with DPS")
    print("  - Run 'python attack_demo.py' to benchmark all four attack types")
    print("=" * 80)
    
    return history


if __name__ == "__main__":
    # Set random seeds for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Run simulation
    history = main()
