# ASH-FL: Federated Learning Simulator

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Verify
python test_setup.py

# Phase 1 — clean baseline (5-10 min)
python main.py

# Phase 2 — attack demo (all four attack types back-to-back)
python attack_demo.py
```

## What It Does

- **Dataset**: UCI Heart Disease (auto-downloaded, 297 samples, 13 features)
- **Model**: 3-layer neural network (13→32→32→1)
- **FL Setup**: 5 clients, 3 rounds, FedAvg aggregation
- **Privacy**: Server never sees raw data, only model weights

## Files

```
configs/sim_config.yaml        - Hyperparameters + attack config block
clients/data_loader.py         - Dataset loading & IID partitioning
clients/client.py              - PyTorch model + Flower client
aggregation/strategy.py        - FedAvg aggregation (unchanged)
attacks/__init__.py            - Attack package & registry
attacks/base.py                - AttackConfig dataclass + BaseAttack ABC
attacks/label_flip.py          - Label-flipping attack
attacks/sign_flip.py           - Sign-flipping (gradient reversal) attack
attacks/scaling.py             - Update scaling / amplification attack
attacks/backdoor.py            - Backdoor (trigger injection) attack
attacks/malicious_client.py    - MaliciousClient wrapping HeartDiseaseClient
attacks/client_factory.py      - Extended factory with ground-truth labels
main.py                        - Run simulation (clean or attacked)
attack_demo.py                 - Phase 2 benchmark: baseline vs 4 attacks
demo_quick.py                  - Fast sanity-check (Phase 1)
```

## How It Works (Simulation Mode)

- Single Python process on your machine
- No actual network/servers (Flower simulates it in memory)
- Data partitioned at startup, clients created on-demand per round
- Fast for research, not realistic network conditions

## Enabling Attacks (Phase 2)

Edit `configs/sim_config.yaml`:
```yaml
attack:
  enabled: true
  attack_type: "label_flip"    # label_flip | sign_flip | scaling | backdoor
  num_malicious_clients: 1
  source_label: 0
  target_label: 1
```
Then run `python main.py` — clean behaviour is restored by setting `enabled: false`.

## Customize

Edit `configs/sim_config.yaml`:
```yaml
num_rounds: 5              # Change FL rounds
num_clients_total: 5       # Change total clients
learning_rate: 0.01        # Adjust learning rate
local_epochs: 3            # Local training epochs
```

## Next: Phase 3 (DPS + Robust Aggregation)

1. Implement Dynamic Poisoning Score (DPS) — per-client anomaly metric
2. Use `ground_truth` dict from `get_client_fn_with_attacks()` to measure detection accuracy
3. Add robust aggregation strategies (Krum, Trimmed Mean, Coordinate-wise Median)
4. Build adaptive recovery controller
