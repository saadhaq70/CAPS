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
# System test (verify all components work)
python3 test_system.py

# CLI simulations (for scripting/automation)
python main.py                      # Clean baseline
python tests/attack_demo.py         # All 4 attacks
python tests/self_healing_demo.py   # Self-healing demo

# OLD DASHBOARDS (DEPRECATED - use unified dashboard instead)
# bash run_dashboard.sh              # Plain UI, broken recovery counter
# streamlit run app.py               # Beautiful UI, fake numbers
```

## ✨ Unified Dashboard (Recommended)

**The unified dashboard is the single entry point for all ASH-FL features.**

**Launch:**
```bash
bash run_unified.sh
```

**What you get:**
- 🎨 **Cyber HUD Design**: Beautiful neon glassmorphism UI
- 🎯 **Real Functionality**: Actual DPS, attacks, and self-healing (not simulated!)
- 🐛 **Fixed Bugs**: Recovery counter works correctly
- 📊 **Complete Features**: Network topology, DPS analysis, FSM states, trust evolution
- 🛡️ **Self-Healing Demo**: Watch automatic recovery in action

**All features in one dashboard - no need to run multiple apps!**

See [UNIFIED_DASHBOARD.md](UNIFIED_DASHBOARD.md) for detailed documentation.

## What's Included

- **FL Baseline**: FedAvg on UCI Heart Disease dataset
- **4 Attacks**: label_flip, sign_flip, scaling, backdoor (per-client configuration)
- **DPS Detection**: Real-time G, C, H, P, D scores with shadow validation
- **Self-Healing**: FSM-based automatic recovery with checkpoint restoration
- **Unified Dashboard**: Cyber HUD design + real simulation + all features ⭐
- **Tests**: 20 tests, all passing

**Note:** Old dashboards (`app.py`, `dashboard_app.py`) are deprecated. Use `unified_dashboard.py` via `bash run_unified.sh`.

## Dashboard Features

### 🔍 Detection
- Real-time DPS calculation (not fake!)
- 5 signals: G (gradient deviation), C (cosine disagreement), H (history), P (performance impact), D (data quality)
- Shadow validation for P signal (tests updates on clean data)
- Per-client anomaly analysis with radar charts

### 🎯 Attacks
- **Per-client attack assignment**: Configure each client individually
- **4 attack types**: Scaling (amplify gradients), Label-Flip (flip labels), Sign-Flip (reverse gradients), Backdoor
- **Quick presets**: "2 Scaling", "2 Label-Flip", "Mixed Attacks"
- **Configurable intensity**: Adjust attack strength

### 🛡️ Self-Healing
- **Automatic detection**: Triggers when DPS > threshold
- **Client quarantine**: Reduces malicious client weight to 0.1×
- **Checkpoint restoration**: Reverts to last trusted model
- **FSM states**: NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME
- **Recovery tracking**: Fixed counter now shows actual attempts

### 🎨 Cyber HUD Design
- **Fonts**: Orbitron (headers), Space Grotesk (body), JetBrains Mono (code)
- **Colors**: Neon cyan, green, purple with glowing effects
- **Theme**: Dark radial gradient with glassmorphism cards
- **Inspired by**: khaledoghli.com

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
