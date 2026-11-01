# ASH-FL / CAPS

This repository is a local federated-learning simulation for binary heart-disease classification. It trains simulated clients on the Cleveland subset of the UCI Heart Disease dataset and can inject adversarial client updates to compare detection, aggregation, and recovery behavior. It is a research/teaching simulation, not a clinical tool or a deployment with real hospitals or devices.

## Run it

```bash
pip install -r requirements.txt
bash run_unified.sh
```

The dashboard runs a fresh simulation using the selected configuration. For command-line runs, use `python main.py`. To run a defense comparison, use `python -m runners.comparison_runner --attack label_flip` or `--all`. Configuration defaults are in `configs/sim_config.yaml`.

## Dataset

The source data is bundled at `data/processed.cleveland.data` (303 source records). The loader drops rows with missing fields (the commonly observed complete set has 297 records), maps target values 1–4 to the positive class, uses a seeded stratified train/test split, fits feature scaling on training data, and partitions the training rows across simulated clients. Row counts in each split depend on the configured split fraction.

Source: [UCI Heart Disease dataset, ID 45](https://archive.ics.uci.edu/dataset/45/heart+disease). Citation: Janosi, A., Steinbrunn, W., Pfisterer, M., & Detrano, R. (1989), *Heart Disease*, [doi:10.24432/C52P4X](https://doi.org/10.24432/C52P4X). The dataset is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). SHA-256 of the bundled file: `a74b7efa387bc9d108d7d0115d831fe9b414b29ae7124f331b622b4efa0427c8`.

## Results and scope

Displayed metrics are computed from the current simulation run. JSON files already under `results/` are historical artifacts; their exact input and execution provenance are unknown, so they should not be treated as verified benchmark results. DPS signals are heuristic indicators within this simulator, not a guarantee that attacks will be detected. Attack behavior is injected into simulated clients.

See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for the directory map, simulation flow, and feature details.
