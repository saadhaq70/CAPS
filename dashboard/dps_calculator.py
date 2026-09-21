"""
DPS Calculator
Computes Dynamic Poisoning Scores with G, C, H, P, D signal breakdown.

FIXED VERSION:
- P: Real performance impact via shadow validation
- D: Disabled (set to 0.0) - requires local data access
- H: Improved to use feature vector EMA instead of raw parameters
- All signals normalized to [0, 1] range
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from copy import deepcopy


class DPSCalculator:
    """Calculate Dynamic Poisoning Scores with detailed signal breakdown."""
    
    def __init__(self, num_clients: int, model_template: Optional[nn.Module] = None,
                 validation_data: Optional[Tuple] = None):
        """
        Initialize DPS calculator.
        
        Args:
            num_clients: Total number of clients
            model_template: PyTorch model for P computation (shadow validation)
            validation_data: Clean validation set (X, y) for P computation
        """
        self.num_clients = num_clients
        self.model_template = model_template
        self.validation_data = validation_data
        
        # Client history: store feature vectors instead of raw updates
        # Feature vector: [G, C, update_norm, update_mean, update_std]
        self.feature_history = defaultdict(list)
        
        # Store last computed signals for visualization
        self.last_G_scores = {}
        self.last_C_scores = {}
        self.last_H_scores = {}
        self.last_P_scores = {}
        self.last_D_scores = {}
        
        # Store baseline model for P computation
        self.baseline_params = None
    
    def set_baseline_model(self, params: List[np.ndarray]):
        """Set the current global model as baseline for P computation."""
        self.baseline_params = [p.copy() for p in params]
    
    def compute_dps_scores(self, client_updates: List[np.ndarray],
                          client_ids: List[int], 
                          round_num: int,
                          global_params: Optional[List[np.ndarray]] = None) -> Dict[int, float]:
        """
        Compute DPS scores for clients.
        
        Args:
            client_updates: List of parameter arrays from clients
            client_ids: List of client IDs
            round_num: Current round number
            global_params: Current global model parameters (for P computation)
            
        Returns:
            Dictionary mapping client_id to DPS score
        """
        if len(client_updates) < 2:
            # Not enough clients to compute meaningful scores
            return {cid: 0.0 for cid in client_ids}
        
        # Update baseline if provided
        if global_params is not None:
            self.set_baseline_model(global_params)
        
        dps_scores = {}
        
        # Flatten updates for distance calculations
        flat_updates = [self._flatten_params(params) for params in client_updates]
        
        # Compute median update (robust to outliers)
        median_update = np.median(flat_updates, axis=0)
        
        # Compute MAD (Median Absolute Deviation) for normalization
        mad = np.median(np.abs(flat_updates - median_update), axis=0)
        mad = np.where(mad < 1e-8, 1e-8, mad)  # Avoid division by zero
        
        for idx, cid in enumerate(client_ids):
            update = flat_updates[idx]
            
            # G: Gradient Deviation Score (unchanged - already good)
            G_raw = self._compute_G(update, median_update, mad)
            G = self._normalize_score(G_raw, score_type='G')
            
            # C: Cosine Disagreement Score (unchanged - already good)
            C_raw = self._compute_C(update, median_update)
            C = self._normalize_score(C_raw, score_type='C')
            
            # H: History Deviation Score (IMPROVED - uses feature vectors)
            H_raw = self._compute_H_improved(update, median_update, cid, round_num)
            H = self._normalize_score(H_raw, score_type='H')
            
            # P: Performance Impact Score (FIXED - real shadow validation)
            P_raw = self._compute_P_real(client_updates[idx], cid)
            P = self._normalize_score(P_raw, score_type='P')
            
            # D: Data Quality Score (HONEST - disabled, set to 0)
            # REASON: Requires access to local data distribution which violates FL privacy
            # Cannot be computed without raw data access
            D = 0.0
            
            # Combine scores (weighted average)
            # D weight redistributed to other signals
            # IMPORTANT: Scores are normalized to [0,1], so DPS range is also [0,1]
            # Threshold for suspicious: DPS > 0.7 (not > 2.0!)
            weights = {'G': 0.33, 'C': 0.28, 'H': 0.22, 'P': 0.17, 'D': 0.00}
            dps = (weights['G'] * G +
                   weights['C'] * C +
                   weights['H'] * H +
                   weights['P'] * P +
                   weights['D'] * D)
            
            # Debug: Print individual scores for high DPS
            if dps > 0.5:
                print(f"    Client {cid}: G={G:.3f}, C={C:.3f}, H={H:.3f}, P={P:.3f} → DPS={dps:.3f}")
            
            dps_scores[cid] = dps
            
            # Store individual scores for visualization (normalized)
            self.last_G_scores[cid] = G
            self.last_C_scores[cid] = C
            self.last_H_scores[cid] = H
            self.last_P_scores[cid] = P
            self.last_D_scores[cid] = D
        
        # Fill in 0 for non-participating clients
        for cid in range(self.num_clients):
            if cid not in client_ids:
                dps_scores[cid] = 0.0
                self.last_G_scores[cid] = 0.0
                self.last_C_scores[cid] = 0.0
                self.last_H_scores[cid] = 0.0
                self.last_P_scores[cid] = 0.0
                self.last_D_scores[cid] = 0.0
        
        return dps_scores
    
    def _compute_G(self, update: np.ndarray, median: np.ndarray, mad: np.ndarray) -> float:
        """
        Compute G: Gradient Deviation Score.
        Measures distance from median normalized by MAD.
        Range: typically 0-5, with >2 being suspicious.
        """
        deviation = np.abs(update - median)
        normalized_deviation = deviation / mad
        G = np.mean(normalized_deviation)
        return float(G)
    
    def _compute_C(self, update: np.ndarray, median: np.ndarray) -> float:
        """
        Compute C: Cosine Disagreement Score.
        Measures angular distance from consensus direction.
        Range: 0 (perfect agreement) to 2 (opposite direction).
        """
        # Cosine similarity
        dot_product = np.dot(update, median)
        norm_product = np.linalg.norm(update) * np.linalg.norm(median)
        
        if norm_product < 1e-8:
            cosine_sim = 1.0
        else:
            cosine_sim = dot_product / norm_product
            cosine_sim = np.clip(cosine_sim, -1.0, 1.0)
        
        # Convert to disagreement (0 = perfect agreement, 2 = opposite)
        C = 1.0 - cosine_sim
        return float(C)
    
    def _compute_H_improved(self, update: np.ndarray, median: np.ndarray, 
                           client_id: int, round_num: int) -> float:
        """
        Compute H: History Deviation Score (IMPROVED).
        Uses compact feature vector EMA instead of raw parameter EMA.
        
        Feature vector: [G_value, C_value, norm, mean, std]
        This is much more efficient and captures behavioral profile.
        """
        # Extract features from current update
        current_features = self._extract_features(update, median)
        
        # Get historical features
        history = self.feature_history.get(client_id, [])
        
        if len(history) < 2:
            # Not enough history yet - store current and return 0
            self.feature_history[client_id].append(current_features)
            return 0.0
        
        # Compute EMA of historical feature vectors
        ema_features = history[0]
        alpha = 0.3  # EMA decay factor
        for hist_features in history[1:]:
            ema_features = alpha * np.array(hist_features) + (1 - alpha) * np.array(ema_features)
        
        # Compute deviation from EMA
        feature_array = np.array([f if f is not None else 0.0 for f in history])
        std_features = np.std(feature_array, axis=0)
        std_features = np.where(std_features < 1e-8, 1e-8, std_features)
        
        deviation = np.abs(np.array(current_features) - ema_features)
        normalized_deviation = deviation / std_features
        H = np.mean(normalized_deviation)
        
        # Update history (keep last 10 rounds)
        self.feature_history[client_id].append(current_features)
        if len(self.feature_history[client_id]) > 10:
            self.feature_history[client_id].pop(0)
        
        return float(H)
    
    def _extract_features(self, update: np.ndarray, median: np.ndarray) -> List[float]:
        """Extract compact feature vector from update."""
        # Compute MAD for local normalization
        mad_local = np.median(np.abs(update - median))
        if mad_local < 1e-8:
            mad_local = 1e-8
        
        features = [
            np.mean(np.abs(update - median)) / mad_local,  # Relative deviation
            1.0 - np.corrcoef(update, median)[0, 1] if len(update) > 1 else 0.0,  # Correlation disagreement
            float(np.linalg.norm(update)),  # L2 norm
            float(np.mean(update)),  # Mean
            float(np.std(update))  # Std
        ]
        return features
    
    def _compute_P_real(self, client_params: List[np.ndarray], client_id: int) -> float:
        """
        Compute P: Performance Impact Score (REAL IMPLEMENTATION).
        
        Uses shadow validation: temporarily applies the client update to a copy
        of the global model and measures the accuracy drop on clean validation set.
        
        Returns:
            Score in [0, inf] where higher = more harmful
            0 = no degradation, 1 = significant degradation
        """
        # If no validation data or model, fall back to distance-based approximation
        if self.validation_data is None or self.model_template is None or self.baseline_params is None:
            # Fallback: use relative norm as proxy (updates with large norm often hurt)
            norm = np.linalg.norm(self._flatten_params(client_params))
            return min(norm / 10.0, 2.0)  # Crude proxy
        
        try:
            # Create shadow model with baseline parameters
            shadow_model = deepcopy(self.model_template)
            self._set_model_params(shadow_model, self.baseline_params)
            
            # Get baseline accuracy
            baseline_acc = self._evaluate_model(shadow_model)
            
            # Apply client update
            self._set_model_params(shadow_model, client_params)
            
            # Get accuracy after client update
            updated_acc = self._evaluate_model(shadow_model)
            
            # Compute degradation (negative = harmful)
            degradation = baseline_acc - updated_acc
            
            # Convert to score: positive degradation = high P score
            # Scale: 0.1 drop in accuracy = P score of 1.0
            P = max(0.0, degradation / 0.1)
            
            return float(P)
            
        except Exception as e:
            # If shadow validation fails, return 0 (neutral)
            print(f"Warning: P computation failed for client {client_id}: {e}")
            return 0.0
    
    def _evaluate_model(self, model: nn.Module) -> float:
        """Evaluate model on validation set and return accuracy."""
        if self.validation_data is None:
            return 0.0
        
        X_val, y_val = self.validation_data
        model.eval()
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_val)
            y_tensor = torch.FloatTensor(y_val).unsqueeze(1)
            
            outputs = model(X_tensor)
            predictions = (outputs > 0.5).float()
            accuracy = (predictions == y_tensor).float().mean().item()
        
        return accuracy
    
    def _set_model_params(self, model: nn.Module, params: List[np.ndarray]):
        """Set model parameters from numpy arrays."""
        state_dict = model.state_dict()
        param_idx = 0
        
        for key in state_dict.keys():
            if param_idx < len(params):
                state_dict[key] = torch.from_numpy(params[param_idx]).float()
                param_idx += 1
        
        model.load_state_dict(state_dict)
    
    def _normalize_score(self, score: float, score_type: str) -> float:
        """
        Normalize scores to [0, 1] range for consistent weighting.
        
        Typical ranges:
        - G: 0-5 (>2 suspicious)
        - C: 0-2 (>1 suspicious)
        - H: 0-3 (>2 suspicious)
        - P: 0-2 (>0.5 suspicious)
        - D: 0-1 (already normalized)
        """
        if score_type == 'G':
            # G > 2 is suspicious, normalize to [0, 1]
            return min(score / 2.0, 1.0)
        elif score_type == 'C':
            # C > 1 is suspicious (orthogonal or opposite)
            return min(score / 1.0, 1.0)
        elif score_type == 'H':
            # H > 2 is suspicious
            return min(score / 2.0, 1.0)
        elif score_type == 'P':
            # P > 1 is very harmful
            return min(score / 1.0, 1.0)
        else:  # D
            # Already in [0, 1]
            return score
    
    def _flatten_params(self, params: List[np.ndarray]) -> np.ndarray:
        """Flatten parameter list to single vector."""
        return np.concatenate([p.flatten() for p in params])
