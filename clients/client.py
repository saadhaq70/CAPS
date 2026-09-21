"""
Federated Learning Client Implementation
Defines the neural network model and Flower client for local training.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import flwr as fl
from typing import Dict, List, Tuple, Optional
import numpy as np
from collections import OrderedDict


class HeartDiseaseNet(nn.Module):
    """
    Improved neural network for binary classification on tabular data.
    
    Architecture: Input → 64 → 32 → 1 (with ReLU activations)
    Uses deeper capacity for better feature learning.
    """
    
    def __init__(self, input_dim: int = 13, hidden_dim: int = 64, output_dim: int = 1):
        """
        Initialize neural network.
        
        Args:
            input_dim: Number of input features (13 for Heart Disease)
            hidden_dim: Number of neurons in first hidden layer (default: 64)
            output_dim: Number of output neurons (1 for binary classification)
        """
        super(HeartDiseaseNet, self).__init__()
        
        # Two hidden layers for increased capacity
        # 13 → 64 → 32 → 1
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),  # Light dropout for regularization
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        """Forward pass through the network."""
        return self.network(x)


def get_model_parameters(model: nn.Module) -> List[np.ndarray]:
    """
    Extract model parameters as a list of NumPy arrays.
    
    Args:
        model: PyTorch model
        
    Returns:
        List of parameter arrays
    """
    return [param.cpu().detach().numpy() for param in model.parameters()]


def set_model_parameters(model: nn.Module, parameters: List[np.ndarray]) -> None:
    """
    Set model parameters from a list of NumPy arrays.
    
    Args:
        model: PyTorch model
        parameters: List of parameter arrays
    """
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
    model.load_state_dict(state_dict, strict=True)


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    epochs: int,
    learning_rate: float,
    device: torch.device,
    optimizer_type: str = "adam"
) -> Tuple[int, float]:
    """
    Train model on local client data.
    
    Args:
        model: Neural network model
        train_loader: DataLoader for training data
        epochs: Number of local training epochs
        learning_rate: Learning rate for optimizer
        device: Device to train on (cpu or cuda)
        optimizer_type: Type of optimizer ("adam" or "sgd")
        
    Returns:
        Tuple of (num_samples, average_loss)
    """
    model.to(device)
    model.train()
    
    criterion = nn.BCELoss()
    
    # Use Adam optimizer with weight decay for better convergence
    if optimizer_type.lower() == "adam":
        optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=1e-5,  # L2 regularization
            betas=(0.9, 0.999)
        )
    else:
        optimizer = optim.SGD(
            model.parameters(),
            lr=learning_rate,
            weight_decay=1e-5
        )
    
    total_loss = 0.0
    num_batches = 0
    num_samples = 0
    
    for epoch in range(epochs):
        epoch_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch.unsqueeze(1))
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        total_loss += epoch_loss / len(train_loader)
    
    num_samples = len(train_loader.dataset)
    avg_loss = total_loss / epochs
    
    return num_samples, avg_loss


def evaluate_model(
    model: nn.Module,
    test_loader: DataLoader,
    device: torch.device
) -> Tuple[int, float, float]:
    """
    Evaluate model on test data.
    
    Args:
        model: Neural network model
        test_loader: DataLoader for test data
        device: Device to evaluate on
        
    Returns:
        Tuple of (num_samples, loss, accuracy)
    """
    model.to(device)
    model.eval()
    
    criterion = nn.BCELoss()
    
    total_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch.unsqueeze(1))
            
            total_loss += loss.item()
            
            # Binary classification: threshold at 0.5
            predicted = (outputs >= 0.5).float()
            total += y_batch.size(0)
            correct += (predicted.squeeze() == y_batch).sum().item()
    
    num_samples = len(test_loader.dataset)
    avg_loss = total_loss / len(test_loader)
    accuracy = correct / total if total > 0 else 0.0
    
    return num_samples, avg_loss, accuracy


class HeartDiseaseClient(fl.client.NumPyClient):
    """Flower NumPyClient for federated learning."""
    
    def __init__(
        self,
        cid: int,
        X_train: np.ndarray,
        y_train: np.ndarray,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        batch_size: int,
        learning_rate: float,
        local_epochs: int,
        optimizer_type: str = "adam"
    ):
        """
        Initialize federated client.
        
        Args:
            cid: Client ID
            X_train: Training features
            y_train: Training labels
            input_dim: Number of input features
            hidden_dim: Hidden layer dimension
            output_dim: Output dimension
            batch_size: Batch size for training
            learning_rate: Learning rate
            local_epochs: Number of local epochs per round
            optimizer_type: Optimizer type ("adam" or "sgd")
        """
        self.cid = cid
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.local_epochs = local_epochs
        self.optimizer_type = optimizer_type
        
        # Initialize model
        self.model = HeartDiseaseNet(input_dim, hidden_dim, output_dim)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Prepare data loaders
        X_tensor = torch.FloatTensor(X_train)
        y_tensor = torch.FloatTensor(y_train)
        dataset = TensorDataset(X_tensor, y_tensor)
        self.train_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        print(f"Client {cid} initialized with {len(X_train)} samples")
    
    def get_parameters(self, config: Dict) -> List[np.ndarray]:
        """
        Return current model parameters.
        
        Args:
            config: Configuration dictionary (unused in Phase 1)
            
        Returns:
            List of model parameter arrays
        """
        return get_model_parameters(self.model)
    
    def fit(self, parameters: List[np.ndarray], config: Dict) -> Tuple[List[np.ndarray], int, Dict]:
        """
        Train model on local data.
        
        Args:
            parameters: Global model parameters from server
            config: Configuration dictionary
            
        Returns:
            Tuple of (updated_parameters, num_samples, metrics)
        """
        # Update local model with global parameters
        set_model_parameters(self.model, parameters)
        
        # Train on local data with improved optimizer
        num_samples, loss = train_model(
            self.model,
            self.train_loader,
            self.local_epochs,
            self.learning_rate,
            self.device,
            self.optimizer_type
        )
        
        # Return updated model parameters and metrics
        updated_parameters = get_model_parameters(self.model)
        metrics = {"loss": loss}
        
        return updated_parameters, num_samples, metrics
    
    def evaluate(self, parameters: List[np.ndarray], config: Dict) -> Tuple[float, int, Dict]:
        """
        Evaluate model on local data.
        
        Args:
            parameters: Model parameters to evaluate
            config: Configuration dictionary
            
        Returns:
            Tuple of (loss, num_samples, metrics)
        """
        # Update model with received parameters
        set_model_parameters(self.model, parameters)
        
        # Evaluate on local training data (for local metrics)
        num_samples, loss, accuracy = evaluate_model(
            self.model,
            self.train_loader,
            self.device
        )
        
        metrics = {"accuracy": accuracy}
        
        return loss, num_samples, metrics


def get_client_fn(
    client_data: List[Tuple[np.ndarray, np.ndarray]],
    config: Dict
) -> callable:
    """
    Create client factory function for Flower simulation.
    
    Args:
        client_data: List of (X, y) tuples for each client
        config: Configuration dictionary with hyperparameters
        
    Returns:
        Client factory function
    """
    def client_fn(cid: str) -> fl.client.NumPyClient:
        """Create a client instance."""
        client_id = int(cid)
        X_train, y_train = client_data[client_id]
        
        return HeartDiseaseClient(
            cid=client_id,
            X_train=X_train,
            y_train=y_train,
            input_dim=config["input_dim"],
            hidden_dim=config["hidden_dim"],
            output_dim=config["output_dim"],
            batch_size=config["batch_size"],
            learning_rate=config["learning_rate"],
            local_epochs=config["local_epochs"],
            optimizer_type=config.get("optimizer_type", "adam")  # Default to Adam
        )
    
    return client_fn
