"""
Dashboard Simulator (FIXED VERSION)
FL simulator with proper self-healing integration and real DPS computation.

FIXES:
- DPS calculator receives validation data for real P computation
- Self-healing weights actually affect aggregation
- Quarantined clients receive 0.05-0.1x weight multiplier
- Checkpoint restoration properly updates global model
"""

import numpy as np
import torch
from typing import Dict, List, Callable, Optional, Tuple
from collections import defaultdict

from clients.data_loader import HeartDiseaseDataLoader
from clients.client import HeartDiseaseNet, get_model_parameters, set_model_parameters
from attacks.base import AttackConfig
from attacks.client_factory import get_client_fn_with_attacks
from recovery import SelfHealingController
from .dps_calculator import DPSCalculator


class DashboardSimulator:
    """FL simulator with proper self-healing and DPS integration."""
    
    def __init__(self, config: Dict):
        """
        Initialize simulator with configuration.
        
        Args:
            config: Dictionary with simulation parameters
        """
        self.config = config
        self.num_clients = config['num_clients']
        self.num_rounds = config['num_rounds']
        self.random_seed = config['random_seed']
        
        # Set seeds
        np.random.seed(self.random_seed)
        torch.manual_seed(self.random_seed)
        
        # Initialize data
        self._setup_data()
        
        # Initialize model
        self.model = HeartDiseaseNet(input_dim=self.input_dim, hidden_dim=32, output_dim=1)
        self.global_params = get_model_parameters(self.model)
        
        # Initialize results storage BEFORE setting up attacks
        self.results = {
            'rounds': [],
            'ground_truth': {},  # Will be filled by _setup_attacks
            'config': config,
            'events': [],
            'recovery_attempts': 0,
            'checkpoint_count': 0
        }
        
        # Initialize attack configuration
        self._setup_attacks()
        
        # Initialize self-healing if enabled
        if config['enable_self_healing']:
            sh_config = {
                'enabled': True,
                'dps_threshold': config.get('dps_threshold', 0.6),  # Use config value (normalized [0,1])
                'recovery_rounds': config['recovery_rounds'],
                'quarantine_window': 5,
                'suspicious_weight': 0.1,
                'max_recovery_attempts': 3,
                'accuracy_drop_threshold': 0.10,  # FIXED: More sensitive (was 0.15)
                'loss_spike_threshold': 0.25,     # FIXED: More sensitive (was 0.3)
                'suspicious_fraction_threshold': 0.2,  # FIXED: More sensitive (was 0.3) - triggers with 1/5 clients
                'model_drift_threshold': 3.0,     # FIXED: More sensitive (was 5.0)
                'baseline_window': 3,
                'max_checkpoints': 3
            }
            self.sh_controller = SelfHealingController(sh_config)
        else:
            self.sh_controller = None
        
        # Initialize DPS calculator with validation data for real P computation
        # Use a small held-out validation set (20% of test data)
        X_test, y_test = self.test_data
        val_size = int(len(X_test) * 0.5)  # Use 50% for validation
        self.validation_data = (X_test[:val_size], y_test[:val_size])
        self.eval_test_data = (X_test[val_size:], y_test[val_size:])
        
        self.dps_calculator = DPSCalculator(
            self.num_clients,
            model_template=self.model,
            validation_data=self.validation_data
        )
    
    def _setup_data(self):
        """Load and partition dataset."""
        data_loader = HeartDiseaseDataLoader(
            dataset_id=45,
            random_seed=self.random_seed,
            test_split=0.2
        )
        
        federated_data = data_loader.get_federated_data(
            num_clients=self.num_clients,
            iid=True
        )
        
        self.client_datasets = federated_data['client_data']
        self.test_data = federated_data['test_data']
        self.input_dim = federated_data['input_dim']
    
    def _setup_attacks(self):
        """Setup attack configuration with per-client support."""
        if self.config.get('enable_attack', False):
            # Check if we have per-client attack configuration
            client_attacks = self.config.get('client_attacks', {})
            
            if client_attacks:
                # Per-client configuration
                self.per_client_attacks = client_attacks
                malicious_ids = [cid for cid, attack in client_attacks.items() if attack != "none"]
                
                # Use first non-none attack as primary type for legacy compatibility
                primary_attack = next((a for a in client_attacks.values() if a != "none"), "scaling")
                
                attack_config = AttackConfig(
                    enabled=True,
                    attack_type=primary_attack,
                    num_malicious_clients=len(malicious_ids),
                    malicious_client_ids=malicious_ids,
                    source_label=0,
                    target_label=1,
                    scale_factor=self.config.get('scale_factor', 50.0),
                    trigger_feature_indices=[0, 1],
                    trigger_value=1.0,
                    poison_fraction=0.3,
                    backdoor_target_label=1
                )
            else:
                # Legacy single-attack configuration
                self.per_client_attacks = None
                attack_config = AttackConfig(
                    enabled=True,
                    attack_type=self.config.get('attack_type', 'scaling'),
                    num_malicious_clients=self.config.get('num_malicious', 2),
                    malicious_client_ids=[],
                    source_label=0,
                    target_label=1,
                    scale_factor=self.config.get('scale_factor', 50.0),
                    trigger_feature_indices=[0, 1],
                    trigger_value=1.0,
                    poison_fraction=0.3,
                    backdoor_target_label=1
                )
        else:
            self.per_client_attacks = None
            attack_config = AttackConfig(enabled=False)
        
        # Get client factory
        self.client_fn, self.ground_truth = get_client_fn_with_attacks(
            client_data=self.client_datasets,
            config={'input_dim': self.input_dim, 'hidden_dim': 32, 'output_dim': 1,
                   'learning_rate': 0.01, 'batch_size': 16, 'local_epochs': 3},
            attack_config=attack_config,
            per_client_attacks=self.per_client_attacks  # Pass per-client config
        )
        
        # Update ground_truth in results
        self.results['ground_truth'] = self.ground_truth
        
        # Store per-client attack types in results for dashboard display
        if self.per_client_attacks:
            self.results['client_attacks'] = self.per_client_attacks
    
    def run_single_round(self, round_num: int) -> Dict:
        """
        Run a single federated learning round.
        
        Args:
            round_num: Current round number
            
        Returns:
            Complete results up to this round
        """
        # Select clients
        num_selected = min(3, self.num_clients)
        selected_clients = np.random.choice(self.num_clients, num_selected, replace=False)
        
        # Collect client updates
        client_updates = []
        for cid in selected_clients:
            client = self.client_fn(str(cid))
            updated_params, num_samples, _ = client.fit(
                parameters=self.global_params,
                config={"round": round_num}
            )
            client_updates.append((int(cid), updated_params, num_samples))
        
        # FIXED: Compute DPS with real P (shadow validation)
        dps_scores = self.dps_calculator.compute_dps_scores(
            client_updates=[params for _, params, _ in client_updates],
            client_ids=[cid for cid, _, _ in client_updates],
            round_num=round_num,
            global_params=self.global_params
        )
        
        # Debug: Print max DPS and all scores
        if len(dps_scores) > 0:
            max_dps = max(dps_scores.values())
            threshold = self.config.get('dps_threshold', 0.6)
            print(f"  [Round {round_num}] DPS Scores: {[(cid, f'{dps:.3f}') for cid, dps in sorted(dps_scores.items()) if dps > 0]}")
            print(f"  [Round {round_num}] Max DPS: {max_dps:.3f} | Threshold: {threshold}")
            if max_dps > threshold:
                print(f"  [Round {round_num}] ⚠️  ALERT: Max DPS exceeds threshold!")
            else:
                print(f"  [Round {round_num}] ℹ️  Below threshold (need {threshold - max_dps:.3f} more)")
        
        # Fill in 0 for non-selected clients
        for cid in range(self.num_clients):
            if cid not in [c for c, _, _ in client_updates]:
                dps_scores[cid] = 0.0
        
        # Compute trust scores (exponential decay based on DPS)
        trust_scores = {}
        if len(self.results['rounds']) > 0:
            prev_trust = self.results['rounds'][-1]['trust_scores']
            for cid in range(self.num_clients):
                old_trust = prev_trust.get(cid, 1.0)
                dps = dps_scores[cid]
                # Trust decay: trust = trust * (1 - alpha * DPS)
                alpha = 0.1
                new_trust = max(0.01, old_trust * (1 - alpha * min(dps, 1.0)))
                trust_scores[cid] = new_trust
        else:
            trust_scores = {cid: 1.0 for cid in range(self.num_clients)}
        
        # FIXED: Apply self-healing BEFORE aggregation to get quarantine info
        state = 'NORMAL'
        quarantined = []
        recovery_params = None
        
        if self.sh_controller:
            # First, do a preliminary aggregation to get candidate params
            all_params = [params for _, params, _ in client_updates]
            candidate_params = []
            for i in range(len(all_params[0])):
                layer_params = [client_params[i] for client_params in all_params]
                avg_param = np.mean(layer_params, axis=0)
                candidate_params.append(avg_param)
            
            # Evaluate candidate
            set_model_parameters(self.model, candidate_params)
            metrics = self._evaluate_model()
            
            # Update self-healing controller
            final_params, status_msg = self.sh_controller.update(
                round_num=round_num,
                candidate_params=candidate_params,
                metrics=metrics,
                dps_dict=dps_scores,
                reputation=trust_scores,
                client_updates=client_updates
            )
            
            # Get state and quarantine info
            status = self.sh_controller.get_status_summary()
            state = status['state']
            quarantined = [cid for cid in range(self.num_clients)
                          if self.sh_controller.is_client_quarantined(cid)]
            
            # Check if recovery provided different params (checkpoint restore)
            if final_params is not None and state in ['RECOVERY', 'VALIDATE']:
                recovery_params = final_params
            
            # Log events
            if state != 'NORMAL':
                self.results['events'].append({
                    'round': round_num,
                    'message': f"State: {state} | Quarantined: {quarantined}"
                })
            
            # FIXED: Track recovery attempts directly from FSM state, not status message parsing
            # The recovery_attempt_count in the controller tracks actual recovery initiations
            recovery_attempts_from_fsm = status.get('recovery_attempts', 0)
            if recovery_attempts_from_fsm > self.results['recovery_attempts']:
                self.results['recovery_attempts'] = recovery_attempts_from_fsm
        
        # FIXED: Compute aggregation weights with quarantine multipliers
        aggregation_weights = {}
        gamma = 2.0  # Trust sensitivity
        eta = 1.5    # DPS penalty
        
        for cid, _, num_samples in client_updates:
            trust = trust_scores[cid]
            dps = dps_scores[cid]
            
            # Base weight from trust and DPS
            base_weight = num_samples * (trust ** gamma) * ((1 - min(dps / 10.0, 0.99)) ** eta)
            
            # FIXED: Apply quarantine multiplier if client is quarantined
            if self.sh_controller and self.sh_controller.is_client_quarantined(cid):
                quarantine_mult = self.sh_controller.get_client_weight_multiplier(cid)
                weight = base_weight * quarantine_mult
            else:
                weight = base_weight
            
            aggregation_weights[cid] = weight
        
        # Normalize weights
        total_weight = sum(aggregation_weights.values())
        if total_weight > 0:
            aggregation_weights = {k: v / total_weight for k, v in aggregation_weights.items()}
        
        # FIXED: Perform weighted aggregation (not simple average)
        if recovery_params is not None:
            # Use recovery params (checkpoint restore)
            self.global_params = recovery_params
        else:
            # Weighted aggregation based on computed weights
            weighted_params = []
            all_params = [params for _, params, _ in client_updates]
            
            for i in range(len(all_params[0])):
                layer_sum = np.zeros_like(all_params[0][i])
                for (cid, params, _), update_params in zip(client_updates, all_params):
                    weight = aggregation_weights.get(cid, 0.0)
                    layer_sum += weight * update_params[i]
                weighted_params.append(layer_sum)
            
            self.global_params = weighted_params
        
        # Final evaluation with actual global params
        set_model_parameters(self.model, self.global_params)
        metrics = self._evaluate_model()
        
        # Store round results with REAL values
        round_result = {
            'round': round_num,
            'metrics': metrics,
            'dps_scores': dps_scores,
            'trust_scores': trust_scores,
            'aggregation_weights': aggregation_weights,
            'selected_clients': list(selected_clients),
            'state': state,
            'quarantined': quarantined,
            'G_scores': self.dps_calculator.last_G_scores.copy(),
            'C_scores': self.dps_calculator.last_C_scores.copy(),
            'H_scores': self.dps_calculator.last_H_scores.copy(),
            'P_scores': self.dps_calculator.last_P_scores.copy(),
            'D_scores': self.dps_calculator.last_D_scores.copy()
        }
        
        # Update results
        if round_num <= len(self.results['rounds']):
            self.results['rounds'][round_num - 1] = round_result
        else:
            self.results['rounds'].append(round_result)
        
        return self.results
    
    def run_full_simulation(self, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Run complete simulation.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Complete simulation results
        """
        for round_num in range(1, self.num_rounds + 1):
            self.run_single_round(round_num)
            
            if progress_callback:
                progress_callback(round_num, self.num_rounds)
        
        return self.results
    
    def _evaluate_model(self) -> Dict[str, float]:
        """Evaluate model on test set (separate from validation used for P)."""
        X_test, y_test = self.eval_test_data
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_test)
            y_tensor = torch.FloatTensor(y_test).unsqueeze(1)
            
            outputs = self.model(X_tensor)
            loss = torch.nn.functional.binary_cross_entropy(outputs, y_tensor)
            predictions = (outputs > 0.5).float()
            accuracy = (predictions == y_tensor).float().mean().item()
        
        return {
            'accuracy': accuracy,
            'loss': loss.item()
        }
