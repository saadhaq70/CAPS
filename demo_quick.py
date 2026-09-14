"""
Quick demo of ASH-FL Phase 1
Runs a minimal FL simulation for testing purposes.
"""

import sys
import torch
import numpy as np

# Set seeds
torch.manual_seed(42)
np.random.seed(42)

print("=" * 60)
print("ASH-FL Phase 1: Quick Demo")
print("=" * 60)
print("\nStep 1: Testing data loading...")

from clients.data_loader import HeartDiseaseDataLoader

loader = HeartDiseaseDataLoader(dataset_id=45, random_seed=42, test_split=0.2)
federated_data = loader.get_federated_data(num_clients=3, iid=True)

print(f"✓ Dataset loaded: {len(federated_data['client_data'])} clients")
print(f"✓ Test set size: {len(federated_data['test_data'][0])} samples")

print("\nStep 2: Testing model...")
from clients.client import HeartDiseaseNet

model = HeartDiseaseNet(input_dim=13, hidden_dim=32, output_dim=1)
num_params = sum(p.numel() for p in model.parameters())
print(f"✓ Model created with {num_params} parameters")

print("\nStep 3: Running minimal FL simulation (2 rounds, 3 clients)...")
print("This will take 1-2 minutes...\n")

import flwr as fl
from clients.client import get_client_fn
from aggregation.strategy import FedAvgStrategy

# Simplified config
config = {
    "input_dim": 13,
    "hidden_dim": 32,
    "output_dim": 1,
    "batch_size": 16,
    "learning_rate": 0.01,
    "local_epochs": 2,
    "num_rounds": 2
}

# Create client function
client_fn = get_client_fn(federated_data["client_data"], config)

# Create strategy
strategy_wrapper = FedAvgStrategy(
    test_data=federated_data["test_data"],
    config=config,
    fraction_fit=1.0,
    fraction_evaluate=1.0,
    min_fit_clients=3,
    min_evaluate_clients=3,
    min_available_clients=3
)

# Run simulation
history = fl.simulation.start_simulation(
    client_fn=client_fn,
    num_clients=3,
    config=fl.server.ServerConfig(num_rounds=2),
    strategy=strategy_wrapper.get_strategy(),
    client_resources={"num_cpus": 1, "num_gpus": 0.0},
)

print("\n" + "=" * 60)
print("✅ Quick Demo Complete!")
print("=" * 60)

if history.metrics_centralized and "accuracy" in history.metrics_centralized:
    accuracies = [acc for _, acc in history.metrics_centralized["accuracy"]]
    print(f"\nResults:")
    print(f"  Initial Accuracy: {accuracies[0]:.4f}")
    print(f"  Final Accuracy: {accuracies[-1]:.4f}")
    print(f"  Improvement: {(accuracies[-1] - accuracies[0]):.4f}")

print("\n✓ Phase 1 baseline is working correctly!")
print("✓ Run 'python main.py' for the full 5-round simulation")
print("=" * 60)
