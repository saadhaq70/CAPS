# Project structure and features

## What the project does

ASH-FL/CAPS simulates federated learning for binary classification using the bundled Cleveland heart-disease dataset. A central coordinator selects simulated clients, receives their locally trained model updates, aggregates updates, evaluates the global model, and optionally runs attack detection and recovery logic. It does not connect to real patients, hospitals, or physical client devices.

## Simulation flow

1. `configs/sim_config.yaml` supplies training, dataset, attack, and self-healing settings.
2. `clients/data_loader.py` reads `data/processed.cleveland.data`, drops incomplete rows, binarizes the original target, creates a stratified train/test split, scales features using training data, and partitions training samples IID across clients.
3. `clients/client.py` defines the PyTorch classifier and client-side training/evaluation.
4. `attacks/` optionally modifies client labels or model updates for label-flip, sign-flip, scaling, and backdoor scenarios.
5. `aggregation/strategy.py` and the selected defense combine client updates.
6. `dashboard/simulator.py` coordinates local rounds, evaluates metrics, calculates DPS signals, and runs the self-healing state machine when enabled.
7. The dashboard displays metrics and visualizations from that run. Comparison commands save new run outputs under `results/`.

## Directory map

| Path | Purpose |
| --- | --- |
| `data/processed.cleveland.data` | Bundled, original processed Cleveland source file used by the loader. |
| `clients/` | Dataset preprocessing/partitioning, classifier, and federated client training. |
| `configs/sim_config.yaml` | Default rounds, client count, optimizer, data split, attack, and recovery settings. |
| `attacks/` | Attack configuration and simulated malicious-client behaviors. |
| `aggregation/` | Federated averaging strategy. |
| `defenses/` | Multi-Krum, trimmed mean, FLTrust, and ASH-FL comparison implementations and runner. |
| `recovery/` | Health monitoring, checkpoint management, and recovery state machine. |
| `dashboard/` | Simulation orchestration, DPS calculations, educational explanations, and charts. |
| `unified_dashboard.py` | Main Streamlit dashboard implementation. |
| `dashboard/app.py`, `dashboard_app.py`, `app.py` | Compatibility launchers that route to the unified dashboard. |
| `run_unified.sh` | Recommended dashboard launcher. |
| `main.py` | Federated-learning CLI entry point; routes self-healing runs through the integrated simulator. |
| `realtime_simulation.py` | Alternate integrated simulation entry point. |
| `runners/comparison_runner.py`, `run_defense_comparison.py` | Defense/attack comparison CLI entry points. |
| `results/` | Saved comparison and recovery JSON outputs; existing files are historical and have unverified provenance. |
| `tests/` | Test modules and runnable demo scripts. |
| `scratch/` | Diagnostic and investigation scripts, not application entry points. |

## Available features

- **Federated training:** simulated clients train locally; the server aggregates updates with FedAvg.
- **Attack scenarios:** label flipping, sign flipping, update scaling, and backdoor poisoning can be enabled and configured.
- **Defense comparisons:** Multi-Krum, trimmed mean, FLTrust, and ASH-FL are implemented in the comparison runner.
- **DPS monitoring:** gradient, cosine, history, and performance signals are calculated from simulation state; the privacy-sensitive D signal is disabled. These are heuristic signals, not formal proof of malicious behavior.
- **Self-healing:** optional health monitoring, client quarantine/weight adjustment, checkpoint restoration, and recovery transitions.
- **Dashboard:** configurable runs and charts for model performance, signals, trust/aggregation, attack scenario, and recovery state.
- **Full matrix benchmark:** the dashboard can run label-flip, sign-flip, scaling, and backdoor scenarios against ASH-FL, Multi-Krum, Trimmed Mean, and FLTrust in one run. It displays the 16 results in an accuracy heatmap and table, and saves timestamped JSON/CSV outputs under `results/attack_defense_matrix/`.

## Data and result interpretation

The loader expects 14 columns in the local UCI file and raises an error if the file is missing or malformed. It uses only complete rows and fits preprocessing on the training split. The dataset citation, license, and file checksum are in the root [README.md](README.md).

Metrics shown by a fresh run are measurements from that run and its selected configuration. Existing JSON files in `results/` predate the current local-data workflow; their precise provenance cannot be established. Do not cite those artifacts as reproducible results without independently verifying their inputs and run configuration. The project simulates attacks and defenses; its outputs do not establish real-world clinical or security effectiveness.

The current training defaults were selected using stratified five-fold validation on the training partition, with a separate monitoring subset for ASH-FL and no tuning against the final holdout. In a single seeded run (seed 42), the compact configuration (16 hidden units, 3 local epochs, batch size 16, learning rate 0.003, 15 rounds) averaged 82.7% accuracy across those folds versus 79.7% for the previous YAML settings. On the untouched 60-record holdout, it scored 86.7% versus 85.0%. These are results from this dataset split and seed, not a guarantee of future-run accuracy; the holdout difference is one sample.

## Common commands

```bash
# Install dependencies and launch the dashboard
pip install -r requirements.txt
bash run_unified.sh

# Run the configured baseline/CLI simulation
python main.py

# Compare defenses under one attack or all configured attacks
python -m runners.comparison_runner --attack label_flip
python -m runners.comparison_runner --all
```
