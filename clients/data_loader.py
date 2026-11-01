"""Load the bundled UCI Cleveland Heart Disease data for federated clients."""

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "processed.cleveland.data"

# Attribute names in the original processed Cleveland file; the final column is
# the original target (0 = absent, 1–4 = present, with different severity).
FEATURE_NAMES = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
    "exang", "oldpeak", "slope", "ca", "thal",
]
COLUMN_NAMES = FEATURE_NAMES + ["num"]


class HeartDiseaseDataLoader:
    """Read, preprocess, and partition the local 303-row UCI data file."""

    def __init__(
        self,
        dataset_path: str | Path = DEFAULT_DATA_PATH,
        random_seed: int = 42,
        test_split: float = 0.2,
    ):
        self.dataset_path = Path(dataset_path).expanduser().resolve()
        self.random_seed = random_seed
        self.test_split = test_split
        self.scaler = StandardScaler()

    def load_and_preprocess(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Load the original CSV, drop rows marked missing, split and scale it."""
        if not self.dataset_path.is_file():
            raise FileNotFoundError(
                f"Local UCI dataset not found: {self.dataset_path}. "
                "See the root README.md for the official source and setup details."
            )
        if not 0 < self.test_split < 1:
            raise ValueError("test_split must be between 0 and 1")

        frame = pd.read_csv(
            self.dataset_path,
            header=None,
            names=COLUMN_NAMES,
            na_values="?",
            skipinitialspace=True,
        )
        if frame.shape[1] != len(COLUMN_NAMES):
            raise ValueError(f"Expected 14 columns in {self.dataset_path}")
        frame = frame.dropna()
        if frame.empty:
            raise ValueError(f"No complete records found in {self.dataset_path}")

        X = frame[FEATURE_NAMES].to_numpy(dtype=np.float32)
        y_original = frame["num"].to_numpy(dtype=np.int64)
        if not np.isin(y_original, [0, 1, 2, 3, 4]).all():
            raise ValueError("UCI target column must contain values 0 through 4")
        y = (y_original > 0).astype(np.float32)

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=self.test_split,
            random_state=self.random_seed,
            stratify=y,
        )
        X_train = self.scaler.fit_transform(X_train).astype(np.float32)
        X_test = self.scaler.transform(X_test).astype(np.float32)

        print(
            f"Loaded local UCI dataset: {self.dataset_path} "
            f"({len(frame)} complete rows; {len(X_train)} train, {len(X_test)} test)"
        )
        return X_train, y_train, X_test, y_test

    def partition_iid(
        self, X_train: np.ndarray, y_train: np.ndarray, num_clients: int
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        if num_clients < 1 or num_clients > len(X_train):
            raise ValueError("num_clients must be between 1 and the training row count")
        indices = np.random.default_rng(self.random_seed).permutation(len(X_train))
        partitions = np.array_split(indices, num_clients)
        return [(X_train[idx], y_train[idx]) for idx in partitions]

    def get_federated_data(self, num_clients: int, iid: bool = True) -> Dict:
        if not iid:
            raise NotImplementedError("Non-IID partitioning is not implemented")
        X_train, y_train, X_test, y_test = self.load_and_preprocess()
        client_data = self.partition_iid(X_train, y_train, num_clients)
        return {
            "client_data": client_data,
            "test_data": (X_test, y_test),
            "input_dim": X_train.shape[1],
        }


def load_client_data(
    client_id: int, client_datasets: List[Tuple[np.ndarray, np.ndarray]]
) -> Tuple[np.ndarray, np.ndarray]:
    return client_datasets[client_id]
