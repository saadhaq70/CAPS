"""
DPS Calculator
Computes Dynamic Poisoning Scores with G, C, H, P, D signal breakdown.
"""

import numpy as np
from typing import Dict, List
from collections import defaultdict


class DPSCalculator:
    """Calculate Dynamic Poisoning Scores with detailed signal breakdown."""
    
    def __init__(self, num_clients: int):
        """
        Initialize DPS calculator.
        
        Args:
            num_clients: Total number of clients
        """
        self.num_clients = num_clients
        self.history = defaultdict(list)  # Client update history
        
        # Store last computed signals for visualization
        self.last_G_scores = {}
        self.last_C_scores = {}
        self.last_H_scores = {}
        self.last_P_scores = {}
        self.last_D_scores = {}
    
    def compute_dps_scores(self, client_updates: List[np.ndarray],
                          client_ids: List[int], round_num: int) -> Dict[int, float]:
        """
        Compute DPS scores for clients.
        
        Args:
            client_updates: List of parameter arrays
            client_ids: List of client IDs
            round_num: Current round number
            
        Returns:
            Dictionary mapping client_id to DPS score
        """
        if len(client_updates) < 2:
            # Not enough clients to compute meaningful scores
            return {cid: 0.0 for cid in client_ids}
        
        dps_scores = {}
        
        # Flatten updates for distance calculations
        flat_updates = [self._flatten_params(params) for params in client_updates]
        
        # Compute median update
        median_update = np.median(flat_updates, axis=0)
        
        # Compute MAD (Median Absolute Deviation)
        mad = np.median(np.abs(flat_updates - median_update), axis=0)
        mad = np.where(mad < 1e-8, 1e-8, mad)  # Avoid division by zero
        
        for idx, cid in enumerate(client_ids):
            update = flat_updates[idx]
            
            # G: Gradient Deviation Score
            G = self._compute_G(update, median_update, mad)
            
            # C: Cosine Disagreement Score
            C = self._compute_C(update, median_update)
            
            # H: History Deviation Score
            H = self._compute_H(update, cid, round_num)
            
            # P: Performance Impact Score (simplified)
            P = self._compute_P(update, median_update)
            
            # D: Data Quality Score (simplified)
            D = self._compute_D(cid)
            
            # Combine scores (weighted average)
            weights = {'G': 0.30, 'C': 0.25, 'H': 0.20, 'P': 0.15, 'D': 0.10}
            dps = (weights['G'] * G +
                   weights['C'] * C +
                   weights['H'] * H +
                   weights['P'] * P +
                   weights['D'] * D)
            
            dps_scores[cid] = dps
            
            # Store individual scores for visualization
            self.last_G_scores[cid] = G
            self.last_C_scores[cid] = C
            self.last_H_scores[cid] = H
            self.last_P_scores[cid] = P
            self.last_D_scores[cid] = D
            
            # Update history
            self.history[cid].append(update)
            if len(self.history[cid]) > 10:  # Keep last 10 rounds
                self.history[cid].pop(0)
        
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
        """
        deviation = np.abs(update - median)
        normalized_deviation = deviation / mad
        G = np.mean(normalized_deviation)
        return float(G)
    
    def _compute_C(self, update: np.ndarray, median: np.ndarray) -> float:
        """
        Compute C: Cosine Disagreement Score.
        Measures angular distance from consensus direction.
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
    
    def _compute_H(self, update: np.ndarray, client_id: int, round_num: int) -> float:
        """
        Compute H: History Deviation Score.
        Compares current update to client's historical profile.
        """
        history = self.history.get(client_id, [])
        
        if len(history) < 2:
            # Not enough history yet
            return 0.0
        
        # Compute EMA of historical updates
        ema = history[0]
        alpha = 0.3  # EMA decay factor
        for hist_update in history[1:]:
            ema = alpha * hist_update + (1 - alpha) * ema
        
        # Compute deviation from EMA
        deviation = np.abs(update - ema)
        std = np.std(history, axis=0)
        std = np.where(std < 1e-8, 1e-8, std)
        
        normalized_deviation = deviation / std
        H = np.mean(normalized_deviation)
        
        return float(H)
    
    def _compute_P(self, update: np.ndarray, median: np.ndarray) -> float:
        """
        Compute P: Performance Impact Score (simplified).
        In full implementation, this would use shadow validation.
        For dashboard, we approximate based on distance from median.
        """
        # Simplified: updates far from median likely hurt performance
        distance = np.linalg.norm(update - median)
        median_norm = np.linalg.norm(median)
        
        if median_norm < 1e-8:
            P = 0.0
        else:
            P = distance / median_norm
        
        # Scale to reasonable range
        P = min(P, 2.0)
        
        return float(P)
    
    def _compute_D(self, client_id: int) -> float:
        """
        Compute D: Data Quality Score (simplified).
        In full implementation, this would analyze local data distribution.
        For dashboard, we use a simple heuristic.
        """
        # Simplified: assume uniform quality with slight variation
        # In practice, this would check class balance, feature variance, etc.
        base_quality = 0.5
        variation = 0.1 * np.sin(client_id)  # Deterministic variation
        D = base_quality + variation
        D = np.clip(D, 0.0, 1.0)
        
        return float(D)
    
    def _flatten_params(self, params: List[np.ndarray]) -> np.ndarray:
        """Flatten parameter list to single vector."""
        return np.concatenate([p.flatten() for p in params])
