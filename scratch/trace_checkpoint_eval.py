import os
import sys
import torch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from defenses.runner import ComparisonRunner, ExperimentConfig
from defenses.ash_fl import ASHFLDefense

config = ExperimentConfig(
    num_clients=5,
    num_rounds=5,
    local_epochs=3,
    batch_size=16,
    learning_rate=0.01,
    random_seed=42,
    dataset_id=45,
    scale_factor=50.0,
)

runner = ComparisonRunner(config)
fed_data = runner.client_datasets
val_data = runner.validation_data
eval_data = runner.eval_test_data

print("val_data shape:", val_data[0].shape, "labels distribution:", np.bincount(val_data[1].astype(int)))
print("eval_data shape:", eval_data[0].shape, "labels distribution:", np.bincount(eval_data[1].astype(int)))
