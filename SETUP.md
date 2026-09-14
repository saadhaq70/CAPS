# Setup & Run

## Installation

```bash
pip install -r requirements.txt
```

Required: `torch`, `flwr`, `ucimlrepo`, `sklearn`, `pyyaml`, `numpy`, `pandas`

## Run

```bash
# Verify installation
python test_setup.py

# Quick demo (2 min)
python demo_quick.py

# Full simulation (5-10 min)
python main.py
```

## Expected Output

```
[Round 1] Server-side evaluation - Loss: 0.XXXX, Accuracy: 0.XXXX
[Round 2] ...
[Round 5] ...

Final Accuracy: 0.XXXX (should improve over rounds)
```

## Troubleshooting

**Import errors**: Make sure you're in `/Users/saadansari/CAPS` directory

**Slow performance**: Edit `configs/sim_config.yaml`, reduce `num_rounds` or `num_clients_total`

**Dataset download fails**: Check internet, retry. Dataset auto-downloads from UCI repository first time only

## Configuration

Edit `configs/sim_config.yaml` to change:
- Number of rounds/clients
- Learning rate, batch size, epochs
- Model architecture (hidden_dim)

## Dataset Location

Auto-downloaded from UCI (ID: 45) when first run. Cached by `ucimlrepo` package (usually `~/.cache/ucimlrepo/`). 297 samples, 13 features, binary classification.



CAPS/
├── README.md              # Quick overview
├── SETUP.md              # How to install & run
├── CHANGELOG.md          # Track changes
├── requirements.txt      # Dependencies
├── .gitignore           # Git ignore
│
├── main.py              # Run full simulation
├── demo_quick.py        # Fast test
├── test_setup.py        # Verify install
│
├── configs/
│   └── sim_config.yaml  # All settings
├── clients/
│   ├── data_loader.py   # Dataset
│   └── client.py        # Model + FL client
└── aggregation/
    └── strategy.py      # FedAvg
