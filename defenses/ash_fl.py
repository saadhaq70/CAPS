"""
ASH-FL (Adaptive Self-Healing Federated Learning) Defense.
Primary Capstone Defense with optional, modular baseline additions:
G, C, H, P, D signals → DPS → Trust → Adaptive Aggregation → Quarantine → Health Monitor → Checkpoint Recovery → Self-Healing FSM.

Optional additions (disabled by default):
- Multi-Krum Pre-filtering: detects and excludes geometric outliers prior to adaptive weighting.
- Trimmed Mean Robustness: coordinate-wise extreme trimming during parameter aggregation.
- FLTrust Root Bootstrapping: magnitude normalization and directional trust via clean server root data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from .base import BaseDefense
from clients.client import (
    HeartDiseaseNet,
    get_model_parameters,
    set_model_parameters,
    evaluate_model,
    train_model,
)
from dashboard.dps_calculator import DPSCalculator
from recovery.self_heal import SelfHealingController, HealingState


class ASHFLDefense(BaseDefense):
    """
    Proposed Capstone Defense: Adaptive Self-Healing Federated Learning (ASH-FL).
    Acts as the primary, default, fully functional defense pipeline.
    
    Optional baseline additions (Multi-Krum, Trimmed Mean, FLTrust) can be independently
    enabled on top of the ASH-FL pipeline to provide layered defense-in-depth,
    while quarantine, health monitoring, checkpoints, and FSM recovery remain authoritative.
    """

    def __init__(
        self,
        num_clients: int,
        validation_data: Tuple[np.ndarray, np.ndarray],
        input_dim: int = 13,
        hidden_dim: int = 32,
        output_dim: int = 1,
        dps_threshold: float = 0.55,
        recovery_rounds: int = 3,
        quarantine_window: int = 5,
        suspicious_weight: float = 0.1,
        max_recovery_attempts: int = 3,
        enable_multi_krum: bool = False,
        enable_trimmed_mean: bool = False,
        enable_fltrust: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ASH-FL defense.
        
        Args:
            num_clients: Total participating clients
            validation_data: Clean server root dataset (X, y)
            input_dim: Input feature count
            hidden_dim: Hidden dimension
            output_dim: Output dimension
            dps_threshold: Critical DPS anomaly threshold
            recovery_rounds: Rounds to retrain during FSM recovery
            quarantine_window: Rounds to quarantine suspicious clients
            suspicious_weight: Penalty multiplier for quarantined clients
            max_recovery_attempts: Max FSM recovery attempts
            enable_multi_krum: Optional addition: pre-filter updates via Multi-Krum (default: False)
            enable_trimmed_mean: Optional addition: coordinate-wise trimming during aggregation (default: False)
            enable_fltrust: Optional addition: magnitude normalization via FLTrust root update (default: False)
            config: Additional config options
        """
        # Determine descriptive defense label
        active_additions = []
        if enable_multi_krum: active_additions.append("Multi-Krum")
        if enable_trimmed_mean: active_additions.append("Trimmed Mean")
        if enable_fltrust: active_additions.append("FLTrust")

        if active_additions:
            disp_name = f"ASH-FL + {' + '.join(active_additions)}"
        else:
            disp_name = "ASH-FL (Primary Default)"

        super().__init__(name=disp_name, config=config)

        self.num_clients = num_clients
        self.validation_data = validation_data
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.dps_threshold = dps_threshold

        # Optional baseline controls (disabled by default)
        self.enable_multi_krum = enable_multi_krum
        self.enable_trimmed_mean = enable_trimmed_mean
        self.enable_fltrust = enable_fltrust

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = HeartDiseaseNet(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=output_dim,
        )

        # Validation data loader for candidate evaluation and FLTrust bootstrapping
        X_val, y_val = validation_data
        val_dataset = TensorDataset(
            torch.FloatTensor(X_val),
            torch.FloatTensor(y_val),
        )
        self.val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

        # Self-healing configuration
        self.sh_config = {
            "enabled": True,
            "dps_threshold": dps_threshold,
            "recovery_rounds": recovery_rounds,
            "quarantine_window": quarantine_window,
            "suspicious_weight": suspicious_weight,
            "max_recovery_attempts": max_recovery_attempts,
            "accuracy_drop_threshold": 0.10,
            "loss_spike_threshold": 0.25,
            "suspicious_fraction_threshold": 0.2,
            "model_drift_threshold": 3.0,
            "baseline_window": 3,
            "max_checkpoints": 3,
        }

        # DPS Calculator with validation data for shadow validation (P signal)
        self.dps_calculator = DPSCalculator(
            num_clients=num_clients,
            model_template=self.model,
            validation_data=validation_data,
        )

        # Self-healing controller (FSM)
        self.sh_controller = SelfHealingController(self.sh_config)

        # State tracking
        self.trust_scores: Dict[int, float] = {cid: 1.0 for cid in range(num_clients)}
        self.last_dps_scores: Dict[int, float] = {}
        self.last_aggregation_weights: Dict[int, float] = {}
        self.recovery_attempts: int = 0
        self.checkpoint_count: int = 0

        # Optional addition diagnostics
        self.last_krum_selected: List[int] = []
        self.last_fltrust_cosines: Dict[int, float] = {}

    @property
    def defense_type(self) -> str:
        if self.enable_multi_krum or self.enable_trimmed_mean or self.enable_fltrust:
            return "hybrid_self_healing"
        return "self_healing"

    @property
    def supports_self_healing(self) -> bool:
        return True

    @property
    def supports_explicit_detection(self) -> bool:
        return True

    def reset(self, initial_params: Optional[List[np.ndarray]] = None) -> None:
        """Reset ASH-FL controller, calculator, and trust state."""
        self.trust_scores = {cid: 1.0 for cid in range(self.num_clients)}
        self.last_dps_scores = {}
        self.last_aggregation_weights = {}
        self.recovery_attempts = 0
        self.checkpoint_count = 0
        self.last_krum_selected = []
        self.last_fltrust_cosines = {}

        self.dps_calculator = DPSCalculator(
            num_clients=self.num_clients,
            model_template=self.model,
            validation_data=self.validation_data,
        )
        self.sh_controller = SelfHealingController(self.sh_config)
        if initial_params is not None:
            set_model_parameters(self.model, initial_params)

    @staticmethod
    def _flatten(params: List[np.ndarray]) -> np.ndarray:
        return np.concatenate([p.ravel() for p in params])

    def aggregate(
        self,
        round_num: int,
        client_updates: List[Tuple[int, List[np.ndarray], int]],
        global_params: List[np.ndarray],
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Run ASH-FL aggregation with full DPS, quarantine, and self-healing.
        Seamlessly incorporates optional baseline additions if enabled.
        """
        n = len(client_updates)
        if n == 0:
            return global_params, {"error": "No client updates received"}

        client_ids = [cid for cid, _, _ in client_updates]
        update_params = [params for _, params, _ in client_updates]
        num_layers = len(global_params)

        # ── OPTIONAL ADDITION 1: FLTrust Magnitude Normalization ──
        if self.enable_fltrust:
            # Server computes trusted update g_0 on clean root data
            set_model_parameters(self.model, global_params)
            train_model(
                self.model,
                self.val_loader,
                epochs=3,
                learning_rate=0.01,
                device=self.device,
                optimizer_type="adam",
            )
            server_params = get_model_parameters(self.model)
            g0_delta = [s - g for s, g in zip(server_params, global_params)]
            flat_g0 = self._flatten(g0_delta)
            norm_g0 = float(np.linalg.norm(flat_g0))

            normalized_updates = []
            for idx, p in enumerate(update_params):
                cid = client_ids[idx]
                delta = [layer_p - g for layer_p, g in zip(p, global_params)]
                flat_d = self._flatten(delta)
                norm_d = float(np.linalg.norm(flat_d))

                if norm_d > 1e-9 and norm_g0 > 1e-9:
                    cos_sim = float(np.dot(flat_d, flat_g0) / (norm_d * norm_g0))
                    scale_ratio = norm_g0 / norm_d
                    normed_p = [g + scale_ratio * d for g, d in zip(global_params, delta)]
                else:
                    cos_sim = 0.0
                    normed_p = p

                self.last_fltrust_cosines[cid] = cos_sim
                normalized_updates.append(normed_p)
            update_params = normalized_updates

        # ── OPTIONAL ADDITION 2: Multi-Krum Pre-Filtering ──
        krum_excluded: List[int] = []
        if self.enable_multi_krum and n >= 5:
            # Compute pairwise distances
            flat_vecs = [self._flatten(p) for p in update_params]
            dist_mat = np.zeros((n, n))
            for i in range(n):
                for j in range(i + 1, n):
                    d2 = float(np.sum((flat_vecs[i] - flat_vecs[j]) ** 2))
                    dist_mat[i, j] = d2
                    dist_mat[j, i] = d2

            # Krum score: sum of n - f - 2 = 2 closest neighbors (for f=1)
            num_nbrs = max(1, n - 1 - 2)
            scores = []
            for i in range(n):
                others = sorted([dist_mat[i, j] for j in range(n) if j != i])
                scores.append(sum(others[:num_nbrs]))

            # Select m = n - 1 clients with lowest Krum scores
            m_select = max(1, n - 1)
            sorted_order = sorted(range(n), key=lambda idx: scores[idx])
            selected_indices = set(sorted_order[:m_select])
            self.last_krum_selected = [client_ids[idx] for idx in selected_indices]
            krum_excluded = [client_ids[idx] for idx in range(n) if idx not in selected_indices]

        # ── CORE ASH-FL STEP 1: Compute Multi-Signal DPS Scores ──
        dps_scores = self.dps_calculator.compute_dps_scores(
            client_updates=update_params,
            client_ids=client_ids,
            round_num=round_num,
            global_params=global_params,
        )
        self.last_dps_scores = dps_scores.copy()

        # ── CORE ASH-FL STEP 2: Trust Decay ──
        alpha = 0.1
        for cid in client_ids:
            old_trust = self.trust_scores.get(cid, 1.0)
            dps = dps_scores.get(cid, 0.0)
            new_trust = max(0.01, old_trust * (1.0 - alpha * min(dps, 1.0)))
            self.trust_scores[cid] = new_trust

        # ── CORE ASH-FL STEP 3: Preliminary Candidate Model Evaluation ──
        candidate_params: List[np.ndarray] = []
        for l in range(num_layers):
            layer_params = [p[l] for p in update_params]
            candidate_params.append(np.mean(layer_params, axis=0))

        set_model_parameters(self.model, candidate_params)
        _, candidate_loss, candidate_acc = evaluate_model(
            self.model, self.val_loader, self.device
        )
        candidate_metrics = {"accuracy": candidate_acc, "loss": candidate_loss}

        # ── CORE ASH-FL STEP 4: Update Self-Healing Controller (FSM) ──
        final_params, status_msg = self.sh_controller.update(
            round_num=round_num,
            candidate_params=candidate_params,
            metrics=candidate_metrics,
            dps_dict=dps_scores,
            reputation=self.trust_scores,
            client_updates=client_updates,
        )

        status_summary = self.sh_controller.get_status_summary()
        current_state = status_summary.get("state", "normal")
        quarantined = [
            cid
            for cid in range(self.num_clients)
            if self.sh_controller.is_client_quarantined(cid)
        ]

        # Check if FSM rollback provided restored parameters
        recovery_params = None
        if final_params is not None and current_state.upper() in ["RECOVERY", "VALIDATE"]:
            recovery_params = final_params

        fsm_recovery_count = status_summary.get("recovery_attempts", 0)
        if fsm_recovery_count > self.recovery_attempts:
            self.recovery_attempts = fsm_recovery_count

        self.checkpoint_count = len(self.sh_controller.checkpoint_manager.checkpoints)

        # ── CORE ASH-FL STEP 5: Compute Adaptive Aggregation Weights ──
        gamma = 2.0  # Trust sensitivity
        eta = 1.5    # DPS penalty
        raw_weights: Dict[int, float] = {}

        for cid, _, num_samples in client_updates:
            trust = self.trust_scores.get(cid, 1.0)
            dps = dps_scores.get(cid, 0.0)
            base_w = num_samples * (trust ** gamma) * ((1.0 - min(dps / 10.0, 0.99)) ** eta)

            # Apply quarantine multiplier
            if self.sh_controller.is_client_quarantined(cid):
                q_mult = self.sh_controller.get_client_weight_multiplier(cid)
                weight = base_w * q_mult
            elif cid in krum_excluded:
                # If Multi-Krum pre-filtering is enabled and identified this node as an outlier
                weight = base_w * 0.05
            else:
                weight = base_w

            raw_weights[cid] = max(1e-6, weight)

        total_w = sum(raw_weights.values())
        norm_weights = {cid: w / total_w for cid, w in raw_weights.items()}
        self.last_aggregation_weights = norm_weights

        # ── CORE ASH-FL STEP 6: Final Parameter Aggregation ──
        if recovery_params is not None:
            aggregated_params = [p.copy() for p in recovery_params]
        elif self.enable_trimmed_mean and n >= 5:
            # OPTIONAL ADDITION 3: Coordinate-wise Trimming on updates
            k = 1
            aggregated_params = []
            for l in range(num_layers):
                layer_stack = np.stack([p[l] for p in update_params], axis=0)
                sorted_stack = np.sort(layer_stack, axis=0)
                trimmed_stack = sorted_stack[k : n - k]
                aggregated_params.append(np.mean(trimmed_stack, axis=0))
        else:
            # Original Default ASH-FL weighted average
            aggregated_params = []
            for l in range(num_layers):
                layer_sum = np.zeros_like(global_params[l])
                for idx, (cid, _, _) in enumerate(client_updates):
                    w = norm_weights.get(cid, 0.0)
                    layer_sum += w * update_params[idx][l]
                aggregated_params.append(layer_sum)

        metrics = {
            "dps_scores": self.last_dps_scores,
            "trust_scores": self.trust_scores.copy(),
            "aggregation_weights": self.last_aggregation_weights,
            "G_scores": self.dps_calculator.last_G_scores.copy(),
            "C_scores": self.dps_calculator.last_C_scores.copy(),
            "H_scores": self.dps_calculator.last_H_scores.copy(),
            "P_scores": self.dps_calculator.last_P_scores.copy(),
            "D_scores": self.dps_calculator.last_D_scores.copy(),
            "fsm_state": current_state.upper(),
            "quarantined_clients": quarantined,
            "recovery_attempts": self.recovery_attempts,
            "checkpoint_count": self.checkpoint_count,
            "status_message": status_msg,
            "is_recovering": current_state.upper() in ["RECOVERY", "VALIDATE"],
            "optional_multi_krum_active": self.enable_multi_krum,
            "optional_trimmed_mean_active": self.enable_trimmed_mean,
            "optional_fltrust_active": self.enable_fltrust,
            "krum_selected": self.last_krum_selected,
            "krum_excluded": krum_excluded,
            "fltrust_cosines": self.last_fltrust_cosines,
        }

        return aggregated_params, metrics
