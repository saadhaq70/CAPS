# ASH-FL: Federated Learning Simulator

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Verify
python test_setup.py

# Run simulation (5-10 min)
python main.py
```

## What It Does

- **Dataset**: UCI Heart Disease (auto-downloaded, 297 samples, 13 features)
- **Model**: 3-layer neural network (13→32→32→1)
- **FL Setup**: 10 clients, 5 rounds, FedAvg aggregation
- **Privacy**: Server never sees raw data, only model weights

## Files

```
configs/sim_config.yaml    - Hyperparameters
clients/data_loader.py     - Dataset loading & IID partitioning
clients/client.py          - PyTorch model + Flower client
aggregation/strategy.py    - FedAvg aggregation
main.py                    - Run simulation
```

## How It Works (Simulation Mode)

- Single Python process on your machine
- No actual network/servers (Flower simulates it in memory)
- Data partitioned at startup, clients created on-demand per round
- Fast for research, not realistic network conditions

## Customize

Edit `configs/sim_config.yaml`:
```yaml
num_rounds: 5              # Change FL rounds
num_clients_total: 10      # Change total clients
learning_rate: 0.01        # Adjust learning rate
local_epochs: 5            # Local training epochs
```

## Next: Phase 2 (Security)

1. Add malicious clients (label flipping, poisoning)
2. Implement Dynamic Poisoning Score (DPS)
3. Add robust aggregation (Krum, Trimmed Mean)
4. Build adaptive recovery controller
