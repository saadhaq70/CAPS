"""
Dashboard Simulator
Simplified FL simulator optimized for interactive dashboard use.
"""

import numpy as np
import torch
from typing import Dict, List, Callable, Optional
from collections import defaultdict

from clients.data_loader import HeartDiseaseDataLoader
from clients.client import HeartDiseaseNet, get_model_parameters, set_model_parameters
from attacks.base import AttackConfig
from attacks.client_factory import get_client_fn_with_attacks
from recovery import SelfHealingController
from .dps_calculator import DPSCalculator


class DashboardSimulator:
    """Fast FL simulator for dashboard with detailed metrics tracking."""
    
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
        
        # Initialize attack configuration
        self._setup_attacks()
        
        # Initialize self-healing if enabled
        if config['enable_self_healing']:
            sh_config = {
                'enabled': True,
                'dps_threshold': config['dps_threshold'],
                'recovery_rounds': config['recovery_rounds'],
                'quarantine_window': 5,
                'suspicious_weight': 0.1,
                'max_recovery_attempts': 3,
                'accuracy_drop_threshold': 0.15,
                'loss_spike_threshold': 0.3,
                'suspicious_fraction_threshold': 0.3,
                'model_drift_threshold': 5.0,
                'baseline_window': 3,
                'max_checkpoints': 3
            }
            self.sh_controller = SelfHealingController(sh_config)
        else:
            self.sh_controller = None
        
        # Initialize DPS calculator
        self.dps_calculator = DPSCalculator(self.num_clients)
        
        # Results storage
        self.results = {
            'rounds': [],
            'ground_truth': self.ground_truth,
            'config': config,
            'events': [],
            'recovery_attempts': 0,
            'checkpoint_count': 0
        }
    
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
        """Setup attack configuration."""
        if self.config['enable_attack']:
            attack_config = AttackConfig(
                enabled=True,
                attack_type=self.config['attack_type'],
                num_malicious_clients=self.config['num_malicious'],
                malicious_client_ids=[],
                source_label=0,
                target_label=1,
                scale_factor=self.config['scale_factor'],
                trigger_feature_indices=[0, 1],
                trigger_value=1.0,
                poison_fraction=0.3,
                backdoor_target_label=1
            )
        else:
            attack_config = AttackConfig(enabled=False)
        
        # Get client factory
        self.client_fn, self.ground_truth = get_client_fn_with_attacks(
            client_data=self.client_datasets,
            config={'input_dim': self.input_dim, 'hidden_dim': 32, 'output_dim': 1,
                   'learning_rate': 0.01, 'batch_size': 16, 'local_epochs': 3},
            attack_config=attack_config
        )
    
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
        
        # Aggregate (simple FedAvg)
        all_params = [params for _, params, _ in client_updates]
        candidate_params = []
        for i in range(len(all_params[0])):
            layer_params = [client_params[i] for client_params in all_params]
            avg_param = np.mean(layer_params, axis=0)
            candidate_params.append(avg_param)
        
        # Evaluate on test set
        set_model_parameters(self.model, candidate_params)
        metrics = self._evaluate_model()
        
        # Compute DPS scores for all clients
        dps_scores = self.dps_calculator.compute_dps_scores(
            client_updates=[params for _, params, _ in client_updates],
            client_ids=[cid for cid, _, _ in client_updates],
            round_num=round_num
        )
        
        # Fill in 0 for non-selected clients
        for cid in range(self.num_clients):
            if cid not in [c for c, _, _ in client_updates]:
                dps_scores[cid] = 0.0
        
        # Compute trust scores (simple decay based on DPS)
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
        
        # Compute aggregation weights
        aggregation_weights = {}
        gamma = 2.0  # Trust sensitivity
        eta = 1.5    # DPS penalty
        
        for cid, _, num_samples in client_updates:
            trust = trust_scores[cid]
            dps = dps_scores[cid]
            weight = num_samples * (trust ** gamma) * ((1 - min(dps / 10.0, 0.99)) ** eta)
            aggregation_weights[cid] = weight
        
        # Normalize weights
        total_weight = sum(aggregation_weights.values())
        if total_weight > 0:
            aggregation_weights = {k: v / total_weight for k, v in aggregation_weights.items()}
        
        # Apply self-healing if enabled
        state = 'NORMAL'
        quarantined = []
        
        if self.sh_controller:
            final_params, status_msg = self.sh_controller.update(
                round_num=round_num,
                candidate_params=candidate_params,
                metrics=metrics,
                dps_dict=dps_scores,
                reputation=trust_scores,
                client_updates=client_updates
            )
            
            self.global_params = final_params if final_params is not None else candidate_params
            
            status = self.sh_controller.get_status_summary()
            state = status['state']
            quarantined = [cid for cid in range(self.num_clients)
                          if self.sh_controller.is_client_quarantined(cid)]
            
            # Log events
            if state != 'NORMAL':
                self.results['events'].append({
                    'round': round_num,
                    'message': f"State: {state} | Quarantined: {quarantined}"
                })
            
            if 'recovery' in status_msg.lower():
                self.results['recovery_attempts'] += 1
        else:
            self.global_params = candidate_params
        
        # Store round results
        round_result = {
            'round': round_num,
            'metrics': metrics,
            'dps_scores': dps_scores,
            'trust_scores': trust_scores,
            'aggregation_weights': aggregation_weights,
            'selected_clients': list(selected_clients),
            'state': state,
            'quarantined': quarantined,
            'G_scores': self.dps_calculator.last_G_scores,
            'C_scores': self.dps_calculator.last_C_scores,
            'H_scores': self.dps_calculator.last_H_scores,
            'P_scores': self.dps_calculator.last_P_scores,
            'D_scores': self.dps_calculator.last_D_scores
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
        """Evaluate model on test set."""
        X_test, y_test = self.test_data
        
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
