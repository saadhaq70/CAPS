"""
Data Loader for UCI Heart Disease Dataset
Handles downloading, preprocessing, and IID partitioning for federated clients.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from ucimlrepo import fetch_ucirepo
from typing import Tuple, List, Dict


class HeartDiseaseDataLoader:
    """Loads and partitions UCI Heart Disease dataset for federated learning."""
    
    def __init__(self, dataset_id: int = 45, random_seed: int = 42, test_split: float = 0.2):
        """
        Initialize data loader.
        
        Args:
            dataset_id: UCI repository dataset ID (45 for Heart Disease)
            random_seed: Random seed for reproducibility
            test_split: Fraction of data to reserve for testing
        """
        self.dataset_id = dataset_id
        self.random_seed = random_seed
        self.test_split = test_split
        self.scaler = StandardScaler()
        
        np.random.seed(random_seed)
        
    def load_and_preprocess(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Load UCI Heart Disease dataset and preprocess.
        
        Returns:
            X_train: Training features (scaled)
            y_train: Training labels (binary)
            X_test: Test features (scaled)
            y_test: Test labels (binary)
        """
        print(f"Fetching UCI Heart Disease dataset (ID: {self.dataset_id})...")
        
        # Fetch dataset from UCI repository
        heart_disease = fetch_ucirepo(id=self.dataset_id)
        
        # Extract features and targets
        X = heart_disease.data.features
        y = heart_disease.data.targets
        
        # Handle missing values by dropping rows with NaN
        df = pd.concat([X, y], axis=1).dropna()
        X = df.iloc[:, :-1].values
        y = df.iloc[:, -1].values
        
        # Binarize target: 0 = no disease, 1-4 = disease present
        y_binary = (y > 0).astype(np.float32)
        
        print(f"Dataset shape: {X.shape}, Binary target distribution: {np.bincount(y_binary.astype(int))}")
        
        # Split into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_binary, test_size=self.test_split, random_state=self.random_seed, stratify=y_binary
        )
        
        # Scale features using StandardScaler
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        print(f"Train set: {X_train.shape}, Test set: {X_test.shape}")
        
        return X_train, y_train, X_test, y_test
    
    def partition_iid(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray, 
        num_clients: int
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Partition data into IID subsets for federated clients.
        
        Args:
            X_train: Training features
            y_train: Training labels
            num_clients: Number of clients to partition data for
            
        Returns:
            List of (X_client, y_client) tuples, one per client
        """
        print(f"Partitioning data into {num_clients} IID subsets...")
        
        num_samples = len(X_train)
        indices = np.random.permutation(num_samples)
        
        # Split indices into roughly equal partitions
        partition_size = num_samples // num_clients
        client_data = []
        
        for i in range(num_clients):
            start_idx = i * partition_size
            # Last client gets any remaining samples
            end_idx = start_idx + partition_size if i < num_clients - 1 else num_samples
            
            client_indices = indices[start_idx:end_idx]
            X_client = X_train[client_indices]
            y_client = y_train[client_indices]
            
            client_data.append((X_client, y_client))
            print(f"  Client {i}: {len(X_client)} samples")
        
        return client_data
    
    def get_federated_data(
        self, 
        num_clients: int, 
        iid: bool = True
    ) -> Dict:
        """
        Load dataset and partition for federated learning.
        
        Args:
            num_clients: Number of federated clients
            iid: Whether to use IID partitioning (non-IID not implemented in Phase 1)
            
        Returns:
            Dictionary containing:
                - client_data: List of (X, y) tuples for each client
                - test_data: (X_test, y_test) tuple for global evaluation
                - input_dim: Number of input features
        """
        # Load and preprocess data
        X_train, y_train, X_test, y_test = self.load_and_preprocess()
        
        # Partition training data for clients
        if iid:
            client_data = self.partition_iid(X_train, y_train, num_clients)
        else:
            raise NotImplementedError("Non-IID partitioning will be implemented in future phases")
        
        return {
            "client_data": client_data,
            "test_data": (X_test, y_test),
            "input_dim": X_train.shape[1]
        }


def load_client_data(client_id: int, client_datasets: List[Tuple[np.ndarray, np.ndarray]]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load data for a specific client.
    
    Args:
        client_id: Client identifier (0-indexed)
        client_datasets: List of all client datasets
        
    Returns:
        (X_client, y_client) tuple for the specified client
    """
    return client_datasets[client_id]
