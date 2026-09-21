# Setup & Installation

## Requirements

- Python 3.8+
- pip

## Install

```bash
pip install -r requirements.txt
```

Installs: torch, flwr, streamlit, plotly, numpy, pandas, scikit-learn, pyyaml, ucimlrepo

## Verify

```bash
python tests/test_setup.py
```

Should print "✅ Setup successful!"

## Run Dashboard

```bash
bash run_dashboard.sh
```

Opens at `http://localhost:8501`

## Run Simulations

```bash
# Clean baseline
python main.py

# All attacks
python tests/attack_demo.py

# Self-healing
python tests/self_healing_demo.py

# Real-time integrated
python realtime_simulation.py
```

## Run Tests

```bash
bash run_all_tests.sh                 # All tests
python tests/test_phase3.py           # Unit tests
python tests/test_comprehensive.py    # Comprehensive
python tests/test_integration.py      # Integration
```

## Configuration

Edit `configs/sim_config.yaml`:

```yaml
num_rounds: 10
num_clients_total: 5

attack:
  enabled: true
  attack_type: "sign_flip"
  num_malicious_clients: 2

self_healing:
  enabled: true
  dps_threshold: 2.0
  recovery_rounds: 3
```

## Troubleshooting

**Dashboard won't start:**
```bash
pip install streamlit plotly --upgrade
```

**Import errors:**
```bash
pip install -r requirements.txt
```

**Port 8501 busy:**
```bash
streamlit run dashboard_app.py --server.port 8502
```

## Project Structure

```
├── dashboard_app.py          # Main dashboard
├── dashboard/                # Dashboard modules
├── recovery/                 # Self-healing (Phase 3)
├── attacks/                  # Attack implementations (Phase 2)
├── clients/                  # FL clients & data
├── aggregation/              # FedAvg strategy
├── configs/                  # Configuration files
├── tests/                    # All test files
│   ├── test_setup.py
│   ├── test_phase3.py
│   ├── test_comprehensive.py
│   ├── test_integration.py
│   ├── attack_demo.py
│   └── self_healing_demo.py
├── main.py                   # Clean baseline
└── realtime_simulation.py    # Real-time sim
```

## Dataset

UCI Heart Disease (ID: 45) - auto-downloaded on first run.
- 297 samples, 13 features
- Binary classification (disease/no disease)
- Split: 80% train, 20% test
- Partitioned IID across clients
