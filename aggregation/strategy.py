"""
Federated Aggregation Strategies
Implements FedAvg as baseline; designed for easy extension to robust strategies.
"""

import flwr as fl
from flwr.common import Metrics, NDArrays, Scalar
from flwr.server.strategy import FedAvg
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from clients.client import HeartDiseaseNet, evaluate_model, set_model_parameters


def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    """
    Aggregate metrics from multiple clients using weighted average.
    
    Args:
        metrics: List of (num_samples, metrics_dict) tuples
        
    Returns:
        Aggregated metrics dictionary
    """
    # Extract accuracies and losses
    accuracies = [num_samples * m.get("accuracy", 0.0) for num_samples, m in metrics]
    losses = [num_samples * m.get("loss", 0.0) for num_samples, m in metrics]
    total_samples = sum([num_samples for num_samples, _ in metrics])
    
    # Compute weighted averages
    aggregated_accuracy = sum(accuracies) / total_samples if total_samples > 0 else 0.0
    aggregated_loss = sum(losses) / total_samples if total_samples > 0 else 0.0
    
    return {
        "accuracy": aggregated_accuracy,
        "loss": aggregated_loss
    }


def get_evaluate_fn(
    test_data: Tuple[np.ndarray, np.ndarray],
    config: Dict
) -> callable:
    """
    Create server-side evaluation function for global model testing.
    
    Args:
        test_data: (X_test, y_test) tuple for global evaluation
        config: Configuration dictionary
        
    Returns:
        Evaluation function compatible with Flower strategy
    """
    X_test, y_test = test_data
    
    def evaluate_fn(
        server_round: int,
        parameters: NDArrays,
        config_dict: Dict[str, Scalar]
    ) -> Optional[Tuple[float, Dict[str, Scalar]]]:
        """
        Evaluate global model on centralized test set.
        
        Args:
            server_round: Current federated learning round
            parameters: Global model parameters
            config_dict: Configuration (unused)
            
        Returns:
            Tuple of (loss, metrics_dict) or None
        """
        # Initialize model
        model = HeartDiseaseNet(
            input_dim=config["input_dim"],
            hidden_dim=config["hidden_dim"],
            output_dim=config["output_dim"]
        )
        
        # Set model parameters
        set_model_parameters(model, parameters)
        
        # Prepare test data loader
        X_tensor = torch.FloatTensor(X_test)
        y_tensor = torch.FloatTensor(y_test)
        test_dataset = TensorDataset(X_tensor, y_tensor)
        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
        
        # Evaluate
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        num_samples, loss, accuracy = evaluate_model(model, test_loader, device)
        
        print(f"[Round {server_round}] Server-side evaluation - Loss: {loss:.4f}, Accuracy: {accuracy:.4f}")
        
        return loss, {"accuracy": accuracy, "num_samples": num_samples}
    
    return evaluate_fn


class FedAvgStrategy:
    """
    Wrapper for FedAvg (Federated Averaging) strategy.
    
    This class provides a clean interface for FedAvg and is designed
    to be easily swapped with robust aggregation strategies like:
    - Krum
    - Trimmed Mean
    - Median
    - RFA (Robust Federated Aggregation)
    
    Future phases will extend this to include distance-based detection.
    """
    
    def __init__(
        self,
        test_data: Tuple[np.ndarray, np.ndarray],
        config: Dict,
        fraction_fit: float = 0.5,
        fraction_evaluate: float = 0.5,
        min_fit_clients: int = 5,
        min_evaluate_clients: int = 5,
        min_available_clients: int = 5
    ):
        """
        Initialize FedAvg strategy.
        
        Args:
            test_data: Global test set for server-side evaluation
            config: Configuration dictionary
            fraction_fit: Fraction of clients to sample for training
            fraction_evaluate: Fraction of clients to sample for evaluation
            min_fit_clients: Minimum clients needed for training
            min_evaluate_clients: Minimum clients needed for evaluation
            min_available_clients: Minimum clients that must be available
        """
        self.config = config
        self.test_data = test_data
        
        # Create server-side evaluation function
        evaluate_fn = get_evaluate_fn(test_data, config)
        
        # Initialize FedAvg strategy
        self.strategy = FedAvg(
            fraction_fit=fraction_fit,
            fraction_evaluate=fraction_evaluate,
            min_fit_clients=min_fit_clients,
            min_evaluate_clients=min_evaluate_clients,
            min_available_clients=min_available_clients,
            evaluate_fn=evaluate_fn,
            fit_metrics_aggregation_fn=weighted_average,
            evaluate_metrics_aggregation_fn=weighted_average,
            initial_parameters=None,  # Will be set by server
        )
    
    def get_strategy(self) -> fl.server.strategy.Strategy:
        """
        Get the Flower strategy instance.
        
        Returns:
            Flower strategy object
        """
        return self.strategy


# Future extension point for robust strategies
class RobustAggregationStrategy:
    """
    Placeholder for future robust aggregation strategies.
    
    Will implement:
    - Krum: Selects client updates closest to the majority
    - Trimmed Mean: Removes outliers before averaging
    - Median: Uses coordinate-wise median
    - Custom distance-based methods for ASH-FL
    """
    
    def __init__(self, base_strategy: str = "krum"):
        """
        Initialize robust strategy.
        
        Args:
            base_strategy: Type of robust aggregation ('krum', 'trimmed_mean', 'median')
        """
        self.base_strategy = base_strategy
        raise NotImplementedError(
            f"Robust strategy '{base_strategy}' will be implemented in Phase 2. "
            "Use FedAvgStrategy for Phase 1 baseline."
        )
