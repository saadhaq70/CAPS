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


class AdaptiveStrategy(FedAvg):
    """
    Adaptive Federated Averaging with DPS-based Trust and Self-Healing.
    
    Extends FedAvg to integrate:
    - DPS (Deviation-Performance Score) based trust weights
    - Quarantine multipliers for malicious clients
    - Checkpoint restoration for self-healing
    
    When self-healing is disabled, behaves identically to plain FedAvg.
    """
    
    def __init__(
        self,
        test_data: Tuple[np.ndarray, np.ndarray],
        config: Dict,
        fraction_fit: float = 0.5,
        fraction_evaluate: float = 0.5,
        min_fit_clients: int = 5,
        min_evaluate_clients: int = 5,
        min_available_clients: int = 5,
        self_healing_enabled: bool = True
    ):
        """
        Initialize Adaptive Strategy.
        
        Args:
            test_data: Global test set for server-side evaluation
            config: Configuration dictionary
            fraction_fit: Fraction of clients to sample for training
            fraction_evaluate: Fraction of clients to sample for evaluation
            min_fit_clients: Minimum clients needed for training
            min_evaluate_clients: Minimum clients needed for evaluation
            min_available_clients: Minimum clients that must be available
            self_healing_enabled: Enable DPS-based adaptive weights and quarantine
        """
        self.config = config
        self.test_data = test_data
        self.self_healing_enabled = self_healing_enabled
        
        # Adaptive weights state
        self.dps_scores: Dict[int, float] = {}
        self.trust_scores: Dict[int, float] = {}
        self.quarantine_multipliers: Dict[int, float] = {}
        self.restored_parameters: Optional[NDArrays] = None
        
        # Create server-side evaluation function
        evaluate_fn = get_evaluate_fn(test_data, config)
        
        # Initialize base FedAvg strategy
        super().__init__(
            fraction_fit=fraction_fit,
            fraction_evaluate=fraction_evaluate,
            min_fit_clients=min_fit_clients,
            min_evaluate_clients=min_evaluate_clients,
            min_available_clients=min_available_clients,
            evaluate_fn=evaluate_fn,
            fit_metrics_aggregation_fn=weighted_average,
            evaluate_metrics_aggregation_fn=weighted_average,
            initial_parameters=None,
        )
    
    def update_client_scores(
        self,
        dps_scores: Dict[int, float],
        trust_scores: Dict[int, float],
        quarantine_multipliers: Dict[int, float]
    ):
        """
        Update DPS, trust, and quarantine scores from external detector.
        
        Args:
            dps_scores: Client ID -> DPS score (0-1, higher = more suspicious)
            trust_scores: Client ID -> trust score (0-1, higher = more trustworthy)
            quarantine_multipliers: Client ID -> weight multiplier (0.05-1.0)
        """
        self.dps_scores = dps_scores.copy()
        self.trust_scores = trust_scores.copy()
        self.quarantine_multipliers = quarantine_multipliers.copy()
    
    def set_restored_parameters(self, parameters: Optional[NDArrays]):
        """
        Set restored parameters from checkpoint for self-healing.
        
        Args:
            parameters: Restored model parameters, or None to clear
        """
        self.restored_parameters = parameters
    
    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes]],
        failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes], BaseException]],
    ) -> Tuple[Optional[NDArrays], Dict[str, Scalar]]:
        """
        Aggregate client updates with adaptive weights based on DPS/trust/quarantine.
        
        Args:
            server_round: Current round number
            results: List of (ClientProxy, FitRes) tuples
            failures: List of failed clients
            
        Returns:
            Tuple of (aggregated_parameters, metrics_dict)
        """
        # If checkpoint was restored, use it directly (skip aggregation this round)
        if self.restored_parameters is not None:
            print(f"[Round {server_round}] Using restored checkpoint parameters")
            restored = self.restored_parameters
            self.restored_parameters = None  # Clear after use
            return restored, {}
        
        # If self-healing disabled, use plain FedAvg
        if not self.self_healing_enabled:
            return super().aggregate_fit(server_round, results, failures)
        
        # Extract client IDs and parameters
        weights_results = []
        for client_proxy, fit_res in results:
            # Get client ID (from proxy cid attribute)
            try:
                client_id = int(client_proxy.cid)
            except (AttributeError, ValueError):
                # Fallback: use equal weights if client ID unavailable
                client_id = -1
            
            # Base weight from number of samples
            num_samples = fit_res.num_examples
            
            # Apply adaptive weighting if scores available
            if client_id in self.trust_scores and client_id in self.quarantine_multipliers:
                trust = self.trust_scores[client_id]
                quarantine_mult = self.quarantine_multipliers[client_id]
                
                # Combine trust and quarantine
                # Trust score [0,1] already reflects DPS influence
                # Quarantine multiplier [0.05, 1.0] applies penalty
                adaptive_weight = trust * quarantine_mult
                
                # Final weight: samples * trust * quarantine
                effective_weight = num_samples * adaptive_weight
                
                if adaptive_weight < 0.5:
                    print(f"  Client {client_id}: samples={num_samples}, trust={trust:.3f}, "
                          f"quarantine={quarantine_mult:.3f} → weight={effective_weight:.1f}")
            else:
                # No scores available, use sample count only
                effective_weight = float(num_samples)
            
            weights_results.append((fit_res.parameters, effective_weight))
        
        # Aggregate with adaptive weights
        if not weights_results:
            return None, {}
        
        # Weighted average of parameters
        total_weight = sum(w for _, w in weights_results)
        
        if total_weight == 0:
            print(f"[Round {server_round}] Warning: Total weight is zero, using equal weights")
            # Fallback to equal weights
            total_weight = len(weights_results)
            weights_results = [(params, 1.0) for params, _ in weights_results]
        
        # Convert parameters to arrays and aggregate
        aggregated_arrays = None
        for parameters, weight in weights_results:
            arrays = fl.common.parameters_to_ndarrays(parameters)
            
            if aggregated_arrays is None:
                aggregated_arrays = [arr * (weight / total_weight) for arr in arrays]
            else:
                aggregated_arrays = [
                    agg + arr * (weight / total_weight)
                    for agg, arr in zip(aggregated_arrays, arrays)
                ]
        
        # Convert back to parameters format
        aggregated_params = fl.common.ndarrays_to_parameters(aggregated_arrays)
        
        # Convert to NDArrays for return
        aggregated_ndarrays = fl.common.parameters_to_ndarrays(aggregated_params)
        
        return aggregated_ndarrays, {}


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
