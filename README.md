# ASH-FL: Federated Learning Simulator

Federated Learning with attacks, detection, and self-healing. Interactive web dashboard included.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# System test (verify all components)
python3 test_system.py

# Run dashboard (RECOMMENDED)
bash run_dashboard.sh

# Or run simulations
python main.py                      # Clean baseline
python tests/attack_demo.py         # All 4 attacks
python tests/self_healing_demo.py   # Self-healing demo
python realtime_simulation.py       # Real-time with all features
```

## What's Included

- **FL Baseline**: FedAvg on UCI Heart Disease dataset
- **4 Attacks**: label_flip, sign_flip, scaling, backdoor
- **Self-Healing**: Automatic detection + recovery
- **Dashboard**: Interactive web UI with DPS visualization
- **Tests**: 20 tests, all passing

## Dashboard

`bash run_dashboard.sh` → Opens at `http://localhost:8501`

Configure simulation, run attacks, see DPS scores (G,C,H,P,D), watch self-healing recover.

See `DOCS.md` for details.

## Files

```
configs/sim_config.yaml        - Hyperparameters + attack + self-healing config
clients/data_loader.py         - Dataset loading & IID partitioning
clients/client.py              - PyTorch model + Flower client
aggregation/strategy.py        - FedAvg aggregation
attacks/                       - Attack implementations (Phase 2)
recovery/                      - Self-healing layer (Phase 3)
  ├── health_monitor.py        - Health tracking & degradation detection
  ├── checkpoint_manager.py    - Save/restore trusted models
  └── self_heal.py             - FSM recovery controller
main.py                        - Run simulation
attack_demo.py                 - Phase 2 benchmark
self_healing_demo.py           - Phase 3 self-healing demo
```

## Phase 2: Attacks

Edit `configs/sim_config.yaml`:
```yaml
attack:
  enabled: true
  attack_type: "label_flip"    # label_flip | sign_flip | scaling | backdoor
  num_malicious_clients: 1
```

## Phase 3: Self-Healing

Enable in `configs/sim_config.yaml`:
```yaml
self_healing:
  enabled: true
  dps_threshold: 2.0           # DPS threshold for suspicious clients
  recovery_rounds: 3           # Rounds to retrain during recovery
  quarantine_window: 5         # Rounds to quarantine suspicious clients
  suspicious_weight: 0.1       # Weight for quarantined clients (0-1)
```

**Recovery Flow:**
1. Detect degradation (accuracy drop, loss spike, high DPS, model drift)
2. Identify suspicious clients via DPS
3. Restore last trusted checkpoint
4. Quarantine suspicious clients (down-weight to 0.1)
5. Retrain for 3 rounds from checkpoint
6. Validate: Accept if improved, else expand quarantine
7. Resume normal operation

**FSM States:** NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME

Demo shows automatic recovery from attack injection at rounds 8-12.

## Customize

Edit `configs/sim_config.yaml`:
```yaml
num_rounds: 5              # Change FL rounds
num_clients_total: 5       # Change total clients
learning_rate: 0.01        # Adjust learning rate
local_epochs: 3            # Local training epochs
```
