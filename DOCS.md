# ASH-FL Documentation

## What It Does

Federated Learning simulator with attacks and self-healing on UCI Heart Disease dataset.

## Components

**Phase 1:** Clean FedAvg baseline  
**Phase 2:** 4 attack types (label_flip, sign_flip, scaling, backdoor)  
**Phase 3:** Self-healing with health monitoring, checkpoints, recovery  
**Phase 4:** Interactive Streamlit dashboard  

## Dashboard

Launch: `bash run_dashboard.sh` or `streamlit run dashboard_app.py`

**6 Tabs:**
1. Overview - Quick metrics
2. Attack & Performance - Charts
3. DPS Deep Dive - G,C,H,P,D signals breakdown
4. Trust & Aggregation - Weight evolution
5. Self-Healing Monitor - Recovery timeline
6. Explanations - How it all works

**Controls (sidebar):**
- Clients: 3-10
- Rounds: 5-20
- Attack type: none/label_flip/sign_flip/scaling/backdoor
- Malicious clients: 0 to N-1
- Self-healing: on/off
- DPS threshold: 0.5-5.0

## Key Files

```
dashboard_app.py              # Main dashboard
dashboard/simulator.py        # FL simulation
dashboard/dps_calculator.py   # DPS with G,C,H,P,D
dashboard/visualizations.py   # Charts
dashboard/explanations.py     # Educational content

recovery/                     # Self-healing
  health_monitor.py
  checkpoint_manager.py
  self_heal.py

attacks/                      # Attack implementations
clients/                      # FL clients & data
aggregation/                  # FedAvg strategy
configs/sim_config.yaml       # Configuration
```

## DPS Signals

- **G**: Gradient deviation from median (outlier detection)
- **C**: Cosine disagreement (wrong direction)
- **H**: History deviation (behavior change)
- **P**: Performance impact (accuracy effect)
- **D**: Data quality score

Combined: `DPS = 0.3*G + 0.25*C + 0.2*H + 0.15*P + 0.1*D`

## Self-Healing States

NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME

Triggers on accuracy drop, high DPS, or suspicious fraction.

## Tests

All 20 tests passing:
- `bash run_all_tests.sh` - Run all
- `python test_phase3.py` - Unit tests
- `python test_comprehensive.py` - Comprehensive
- `python test_integration.py` - Integration

## Changes Log

**Latest: Critical Fixes (Rigorously Correct System)**
- Fixed D signal: Honest disable (0.0) instead of fake sin(client_id)
- Fixed P signal: Real shadow validation instead of distance proxy
- Improved H signal: Feature vector EMA instead of raw parameters
- Fixed self-healing: Quarantine weights actually enforced (0.05-0.1x)
- Fixed aggregation: Checkpoint restore actually updates global model
- Fixed DPS: All signals normalized to [0,1] before weighting
- Updated weights: G=0.33, C=0.28, H=0.22, P=0.17, D=0.00
- See `FIXES_SUMMARY.md` for complete details

**Organized tests/** 
- Moved all test files to `tests/` folder
- Updated import paths
- Config reset to defaults (attacks/self-healing disabled)

**Phase 4 (Dashboard):**
- Created interactive Streamlit app
- DPS visualization with radar charts
- Trust/aggregation heatmaps
- Self-healing monitor
- Educational explanations

**Phase 3 (Self-Healing):**
- Health monitoring system
- Checkpoint management
- FSM recovery controller
- Client quarantine mechanism

**Phase 2 (Attacks):**
- 4 attack implementations
- Malicious client factory
- Attack configuration system

**Phase 1 (Baseline):**
- UCI Heart Disease FL simulation
- PyTorch model + Flower framework
- FedAvg aggregation
