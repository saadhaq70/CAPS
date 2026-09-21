# ASH-FL: Adaptive Self-Healing Federated Learning

Federated Learning with attacks, detection, and self-healing. **NEW: Unified Cyber HUD Dashboard** with real functionality.

## 🚀 Quick Start

**Recommended: Use the Unified Dashboard**
```bash
# Install dependencies
pip install -r requirements.txt

# Launch unified dashboard (opens at http://localhost:8501)
bash run_unified.sh
```

**Other options (for specific purposes):**
```bash
# System test (verify all components)
python3 tests/test_system.py

# CLI simulations (for scripting/automation)
python main.py                            # Clean baseline
python tests/attack_demo.py               # All 4 attacks
python tests/self_healing_demo.py         # Self-healing demo

# OLD DASHBOARDS (DEPRECATED - use unified dashboard instead)
# bash run_dashboard.sh                   # Plain UI, broken recovery counter
# streamlit run app.py                    # Beautiful UI, fake numbers
```

## ✨ Unified Dashboard

**Launch:** `bash run_unified.sh`

Features:
- 🎨 Cyber HUD design (neon glassmorphism)
- 🎯 Real DPS (G, C, H, P with shadow validation)
- 🛡️ Self-healing FSM with automatic recovery
- 📊 Network topology, accuracy analysis, aggregation weights
- ⚙️ Per-client attack configuration

## What's Included

- **FL Baseline**: FedAvg on UCI Heart Disease dataset
- **4 Attacks**: label_flip, sign_flip, scaling, backdoor
- **DPS Detection**: Real-time G, C, H, P scores (D disabled for privacy)
- **Self-Healing**: FSM-based recovery with checkpoints
- **Unified Dashboard**: Cyber HUD + real simulation ⭐
- **Tests**: 20 tests, all passing

## Dashboard Features

- **Real DPS**: G (gradient), C (cosine), H (history), P (performance), D (disabled)
- **Attacks**: 4 types with per-client configuration
- **Self-Healing**: Automatic detection → quarantine → recovery
- **Visualization**: Network topology, DPS radar, trust evolution, aggregation weights
- **Cyber HUD**: Orbitron font, neon colors, glassmorphism

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

## Configuration

Edit `configs/sim_config.yaml`:

**Training:**
```yaml
num_rounds: 15
local_epochs: 5
hidden_dim: 64
optimizer_type: "adam"
```

**Attacks:**
```yaml
attack:
  enabled: true
  attack_type: "label_flip"
  num_malicious_clients: 2
```

**Self-Healing:**
```yaml
self_healing:
  enabled: true
  dps_threshold: 0.55
  recovery_rounds: 3
```

## Expected Results

**Clean (no attacks):**
- Final accuracy: 78-88% (typical: 80-85%)
- Smooth convergence in ~10-12 rounds

**With attacks + self-healing:**
- Detection: DPS >0.55 for malicious clients
- Recovery: 1-2 attempts triggered
- Final accuracy: 75-85% (within 3-8% of clean)

See `CHANGES.md` for recent improvements.
