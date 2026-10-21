"""
Common Experiment Runner for Federated Learning Defense Comparison.
Executes Multi-Krum, Trimmed Mean, FLTrust, and ASH-FL under strictly identical conditions.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from clients.client import (
    HeartDiseaseNet,
    get_model_parameters,
    set_model_parameters,
    evaluate_model,
)
from clients.data_loader import HeartDiseaseDataLoader
from attacks.base import AttackConfig
from attacks.client_factory import get_client_fn_with_attacks
from .base import BaseDefense
from .multi_krum import MultiKrumDefense
from .trimmed_mean import TrimmedMeanDefense
from .fltrust import FLTrustDefense
from .ash_fl import ASHFLDefense


@dataclass
class ExperimentConfig:
    """Standardized hyperparameter and dataset configuration."""
    num_clients: int = 5
    num_rounds: int = 3
    local_epochs: int = 3
    batch_size: int = 16
    learning_rate: float = 0.01
    random_seed: int = 42
    dataset_id: int = 45
    test_split: float = 0.2
    iid: bool = True
    input_dim: int = 13
    hidden_dim: int = 32
    output_dim: int = 1

    # Attack configuration
    attack_type: str = "none"  # "none", "label_flip", "sign_flip", "scaling", "backdoor"
    malicious_client_ids: List[int] = field(default_factory=lambda: [1, 2])
    scale_factor: float = 50.0
    source_label: int = 0
    target_label: int = 1
    trigger_feature_indices: List[int] = field(default_factory=lambda: [0, 1])
    trigger_value: float = 1.0
    poison_fraction: float = 0.3
    backdoor_target_label: int = 1


@dataclass
class DefenseResult:
    """Standardized results container for a single defense run."""
    defense_name: str
    attack_type: str
    initial_accuracy: float
    initial_loss: float
    per_round_accuracy: List[float]
    per_round_loss: List[float]
    final_accuracy: float
    final_loss: float
    clean_accuracy: float
    attacked_accuracy: float
    accuracy_degradation: float
    backdoor_asr: Optional[float]
    per_round_backdoor_asr: Optional[List[float]]
    defense_type: str
    supports_self_healing: bool
    supports_explicit_detection: bool
    per_round_defense_metrics: List[Dict[str, Any]]
    recovery_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ComparisonResult:
    """Container for multi-defense comparison results."""

    def __init__(
        self,
        attack_type: str,
        config: Dict[str, Any],
        defense_results: Dict[str, DefenseResult],
    ):
        self.attack_type = attack_type
        self.config = config
        self.defense_results = defense_results
        self.summary_table = self._build_summary_table()

    def _build_summary_table(self) -> List[Dict[str, Any]]:
        table = []
        for name, res in self.defense_results.items():
            row = {
                "Defense": name,
                "Type": res.defense_type.replace("_", " ").title(),
                "Final Accuracy": f"{res.final_accuracy:.1%}",
                "Accuracy Drop": f"{res.accuracy_degradation:+.1%}",
                "Final Loss": f"{res.final_loss:.4f}",
                "Backdoor ASR": f"{res.backdoor_asr:.1%}" if res.backdoor_asr is not None else "N/A",
                "Explicit Detection": "Available" if res.supports_explicit_detection else "N/A (Robust Agg)",
                "Self-Healing": "YES (Autonomous FSM)" if res.supports_self_healing else "N/A",
            }
            if res.supports_self_healing:
                row["Recovery Status"] = (
                    f"Attempts: {res.recovery_metrics.get('recovery_attempts', 0)} | "
                    f"State: {res.recovery_metrics.get('final_fsm_state', 'NORMAL')}"
                )
            else:
                row["Recovery Status"] = "N/A"
            table.append(row)
        return table

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.summary_table)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attack_type": self.attack_type,
            "config": self.config,
            "defense_results": {k: v.to_dict() for k, v in self.defense_results.items()},
            "summary_table": self.summary_table,
        }


def compute_backdoor_asr(
    model: nn.Module,
    eval_test_data: Tuple[np.ndarray, np.ndarray],
    trigger_feature_indices: List[int],
    trigger_value: float,
    backdoor_target_label: int,
    device: torch.device,
) -> float:
    """
    Compute Backdoor Attack Success Rate (ASR) on clean test samples
    whose true label does not equal the target label.
    """
    X_test, y_test = eval_test_data
    non_target_mask = (y_test != backdoor_target_label)
    if not np.any(non_target_mask):
        return 0.0

    X_sub = X_test[non_target_mask].copy()
    for feat_idx in trigger_feature_indices:
        X_sub[:, feat_idx] = trigger_value

    model.eval()
    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_sub).to(device)
        outputs = model(X_tensor)
        preds = (outputs >= 0.5).float().squeeze()
        target_tensor = torch.full_like(preds, float(backdoor_target_label))
        asr = (preds == target_tensor).float().mean().item()
    return float(asr)


class ComparisonRunner:
    """
    Orchestrates defense comparisons ensuring strict fairness and identical experimental conditions.
    """

    def __init__(self, config: Optional[ExperimentConfig] = None):
        self.config = config or ExperimentConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._setup_data_and_base_model()
        self._clean_baseline_cache: Dict[Tuple[str, tuple], float] = {}

    def _setup_data_and_base_model(self) -> None:
        """Load dataset, partition IID for clients, and create initial weights."""
        np.random.seed(self.config.random_seed)
        torch.manual_seed(self.config.random_seed)

        data_loader = HeartDiseaseDataLoader(
            dataset_id=self.config.dataset_id,
            random_seed=self.config.random_seed,
            test_split=self.config.test_split,
        )
        fed_data = data_loader.get_federated_data(
            num_clients=self.config.num_clients,
            iid=self.config.iid,
        )
        self.client_datasets = fed_data["client_data"]
        raw_test_data = fed_data["test_data"]

        # Split test data into clean server root/val set (50%) and evaluation test set (50%)
        # Identical to DashboardSimulator setup
        X_test, y_test = raw_test_data
        val_size = int(len(X_test) * 0.5)
        self.validation_data = (X_test[:val_size], y_test[:val_size])
        self.eval_test_data = (X_test[val_size:], y_test[val_size:])

        # Eval DataLoader
        eval_dataset = TensorDataset(
            torch.FloatTensor(self.eval_test_data[0]),
            torch.FloatTensor(self.eval_test_data[1]),
        )
        self.eval_loader = DataLoader(eval_dataset, batch_size=32, shuffle=False)

        # Base model template initialized with fixed seed
        torch.manual_seed(self.config.random_seed)
        self.eval_model = HeartDiseaseNet(
            input_dim=self.config.input_dim,
            hidden_dim=self.config.hidden_dim,
            output_dim=self.config.output_dim,
        )
        # Store an immutable template of copied parameter arrays to guarantee
        # that initial weights can NEVER be corrupted by PyTorch operations.
        self._initial_params_template = tuple(
            p.copy() for p in get_model_parameters(self.eval_model)
        )
        self.initial_params = list(self.get_initial_parameters())

    def get_initial_parameters(self) -> List[np.ndarray]:
        """Return fresh, independent deep copies of the immutable initial parameters."""
        return [p.copy() for p in self._initial_params_template]

    def _evaluate(self, params: List[np.ndarray]) -> Tuple[float, float]:
        """Evaluate parameters on evaluation test set."""
        set_model_parameters(self.eval_model, params)
        _, loss, acc = evaluate_model(self.eval_model, self.eval_loader, self.device)
        return float(acc), float(loss)

    def get_clean_baseline(self, defense_name: Optional[str] = None) -> float:
        """
        Run or return clean baseline accuracy for a specific defense and configuration.
        Caches per (defense_name, configuration_signature) to prevent cross-config contamination.
        """
        config_key = (
            self.config.dataset_id,
            self.config.test_split,
            self.config.iid,
            self.config.num_clients,
            self.config.num_rounds,
            self.config.local_epochs,
            self.config.batch_size,
            self.config.learning_rate,
            self.config.random_seed,
        )
        cache_key = (defense_name or "Standard_FedAvg", config_key)
        if cache_key in self._clean_baseline_cache:
            return self._clean_baseline_cache[cache_key]

        # Instantiate defense for clean evaluation
        if defense_name and defense_name in self.instantiate_defenses():
            clean_def = self.instantiate_defenses()[defense_name]
        else:
            clean_def = TrimmedMeanDefense(k=0)

        clean_res = self.run_defense(defense=clean_def, attack_type="none")
        self._clean_baseline_cache[cache_key] = clean_res.final_accuracy
        return clean_res.final_accuracy

    def instantiate_defenses(self) -> Dict[str, BaseDefense]:
        """Create fresh instances of all 4 defenses sharing same validation data."""
        return {
            "Multi-Krum": MultiKrumDefense(f=1, m=4),
            "Trimmed Mean": TrimmedMeanDefense(k=1),
            "FLTrust": FLTrustDefense(
                validation_data=self.validation_data,
                input_dim=self.config.input_dim,
                hidden_dim=self.config.hidden_dim,
                output_dim=self.config.output_dim,
                learning_rate=self.config.learning_rate,
                local_epochs=self.config.local_epochs,
                batch_size=self.config.batch_size,
            ),
            "ASH-FL": ASHFLDefense(
                num_clients=self.config.num_clients,
                validation_data=self.validation_data,
                input_dim=self.config.input_dim,
                hidden_dim=self.config.hidden_dim,
                output_dim=self.config.output_dim,
                dps_threshold=0.55,
                recovery_rounds=3,
            ),
        }

    def run_defense(
        self,
        defense: BaseDefense,
        attack_type: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> DefenseResult:
        """
        Execute an experiment for a single defense under strict fairness.
        """
        # Reset RNG seeds so that every defense run (and clean baseline) sees the exact
        # same deterministic sample shuffling and training sequences, guaranteeing
        # strict reproducibility and order invariance.
        torch.manual_seed(self.config.random_seed)
        np.random.seed(self.config.random_seed)

        is_attack = attack_type.lower() != "none"
        attack_config = AttackConfig(
            enabled=is_attack,
            attack_type=attack_type.lower() if is_attack else "none",
            num_malicious_clients=len(self.config.malicious_client_ids) if is_attack else 0,
            malicious_client_ids=self.config.malicious_client_ids if is_attack else [],
            source_label=self.config.source_label,
            target_label=self.config.target_label,
            scale_factor=self.config.scale_factor,
            trigger_feature_indices=self.config.trigger_feature_indices,
            trigger_value=self.config.trigger_value,
            poison_fraction=self.config.poison_fraction,
            backdoor_target_label=self.config.backdoor_target_label,
        )

        client_config = {
            "input_dim": self.config.input_dim,
            "hidden_dim": self.config.hidden_dim,
            "output_dim": self.config.output_dim,
            "learning_rate": self.config.learning_rate,
            "batch_size": self.config.batch_size,
            "local_epochs": self.config.local_epochs,
            "optimizer_type": "adam",
        }

        # Client factory for this run
        client_fn, ground_truth = get_client_fn_with_attacks(
            client_data=self.client_datasets,
            config=client_config,
            attack_config=attack_config,
        )

        # Reset defense to fresh immutable copy of initial parameters
        current_params = self.get_initial_parameters()
        defense.reset(initial_params=[p.copy() for p in current_params])

        # Initial evaluation
        init_acc, init_loss = self._evaluate(current_params)

        per_round_acc: List[float] = []
        per_round_loss: List[float] = []
        per_round_metrics: List[Dict[str, Any]] = []
        per_round_asr: Optional[List[float]] = [] if attack_type.lower() == "backdoor" else None

        for r in range(1, self.config.num_rounds + 1):
            if progress_callback:
                progress_callback(r, self.config.num_rounds, defense.name)

            # Local training across all clients
            client_updates: List[Tuple[int, List[np.ndarray], int]] = []
            for cid in range(self.config.num_clients):
                client = client_fn(str(cid))
                updated_params, num_samples, _ = client.fit(
                    parameters=current_params,
                    config={"round": r},
                )
                client_updates.append((cid, updated_params, num_samples))

            # Defense aggregation
            new_params, def_metrics = defense.aggregate(
                round_num=r,
                client_updates=client_updates,
                global_params=current_params,
            )

            # Server-side evaluation of updated model
            acc, loss = self._evaluate(new_params)
            per_round_acc.append(acc)
            per_round_loss.append(loss)
            per_round_metrics.append(def_metrics)

            if per_round_asr is not None:
                asr = compute_backdoor_asr(
                    model=self.eval_model,
                    eval_test_data=self.eval_test_data,
                    trigger_feature_indices=self.config.trigger_feature_indices,
                    trigger_value=self.config.trigger_value,
                    backdoor_target_label=self.config.backdoor_target_label,
                    device=self.device,
                )
                per_round_asr.append(asr)

            current_params = new_params

        final_acc = per_round_acc[-1] if per_round_acc else init_acc
        final_loss = per_round_loss[-1] if per_round_loss else init_loss
        final_asr = per_round_asr[-1] if per_round_asr is not None else None

        # Clean baseline for degradation calculation (defense-specific and config-isolated)
        clean_acc = self.get_clean_baseline(defense_name=defense.name) if is_attack else final_acc
        attacked_acc = min(per_round_acc) if per_round_acc else final_acc
        acc_drop = clean_acc - final_acc

        # Recovery metrics (specific to self-healing)
        recovery_metrics = {}
        if defense.supports_self_healing:
            last_m = per_round_metrics[-1] if per_round_metrics else {}
            recovery_metrics = {
                "recovery_attempts": last_m.get("recovery_attempts", 0),
                "checkpoint_count": last_m.get("checkpoint_count", 0),
                "final_fsm_state": last_m.get("fsm_state", "NORMAL"),
                "quarantined_clients": last_m.get("quarantined_clients", []),
                "recovery_triggered": last_m.get("recovery_attempts", 0) > 0,
            }

        return DefenseResult(
            defense_name=defense.name,
            attack_type=attack_type,
            initial_accuracy=init_acc,
            initial_loss=init_loss,
            per_round_accuracy=per_round_acc,
            per_round_loss=per_round_loss,
            final_accuracy=final_acc,
            final_loss=final_loss,
            clean_accuracy=clean_acc,
            attacked_accuracy=attacked_acc,
            accuracy_degradation=acc_drop,
            backdoor_asr=final_asr,
            per_round_backdoor_asr=per_round_asr,
            defense_type=defense.defense_type,
            supports_self_healing=defense.supports_self_healing,
            supports_explicit_detection=defense.supports_explicit_detection,
            per_round_defense_metrics=per_round_metrics,
            recovery_metrics=recovery_metrics,
        )

    def run_comparison(
        self,
        attack_type: str,
        defense_names: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> ComparisonResult:
        """Run comparison across specified defenses for a given attack."""
        all_defenses = self.instantiate_defenses()
        names = defense_names or list(all_defenses.keys())

        results: Dict[str, DefenseResult] = {}
        for name in names:
            if name in all_defenses:
                res = self.run_defense(
                    defense=all_defenses[name],
                    attack_type=attack_type,
                    progress_callback=progress_callback,
                )
                results[name] = res

        return ComparisonResult(
            attack_type=attack_type,
            config=asdict(self.config),
            defense_results=results,
        )

    def run_full_matrix(
        self,
        output_dir: str = "results/defense_comparison",
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, ComparisonResult]:
        """
        Execute 4 defenses × 4 attacks = 16 combinations, plus Clean baseline.
        Saves results to JSON and summary CSV.
        """
        os.makedirs(output_dir, exist_ok=True)
        attacks = ["label_flip", "sign_flip", "scaling", "backdoor"]
        matrix_results: Dict[str, ComparisonResult] = {}

        summary_rows = []

        for atk in attacks:
            if progress_callback:
                progress_callback(atk, "Starting comparison")
            comp_res = self.run_comparison(attack_type=atk)
            matrix_results[atk] = comp_res

            # Save individual JSON
            json_path = os.path.join(output_dir, f"{atk}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(comp_res.to_dict(), f, indent=2)

            for row in comp_res.summary_table:
                row_copy = row.copy()
                row_copy["Attack"] = atk.replace("_", " ").title()
                summary_rows.append(row_copy)

        # Save summary CSV
        csv_path = os.path.join(output_dir, "comparison_summary.csv")
        summary_df = pd.DataFrame(summary_rows)
        # Reorder columns with Attack first
        cols = ["Attack"] + [c for c in summary_df.columns if c != "Attack"]
        summary_df = summary_df[cols]
        summary_df.to_csv(csv_path, index=False)

        return matrix_results
