"""
ASH-FL: Real-Time Integrated Simulation
Combines FL pipeline + all attacks + self-healing with live scoring display.
"""

import yaml
import flwr as fl
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import time

from clients.data_loader import HeartDiseaseDataLoader
from clients.client import get_client_fn, HeartDiseaseNet, get_model_parameters, set_model_parameters
from aggregation.strategy import FedAvgStrategy
from attacks.base import AttackConfig
from attacks.client_factory import get_client_fn_with_attacks
from recovery import SelfHealingController, HealthMonitor


class RealTimeSimulation:
    """Real-time federated learning simulation with integrated monitoring."""
    
    def __init__(self, config_path: str = "configs/sim_config.yaml"):
        """Initialize simulation with configuration."""
        self.config = self._load_config(config_path)
        self.metrics_history = []
        self.dps_history = []
        self.state_history = []
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _print_header(self):
        """Print simulation header."""
        print("\n" + "=" * 100)
        print(" " * 30 + "ASH-FL: REAL-TIME INTEGRATED SIMULATION")
        print("=" * 100)
        print(f"{'Configuration:':<20} {self.config['num_rounds']} rounds | "
              f"{self.config['num_clients_total']} clients | "
              f"{self.config['num_clients_per_round']} per round")
        
        # Attack info
        attack_cfg = self.config.get("attack", {})
        if attack_cfg.get("enabled", False):
            print(f"{'Attack Mode:':<20} {attack_cfg['attack_type'].upper()} | "
                  f"{attack_cfg['num_malicious_clients']} malicious client(s)")
        else:
            print(f"{'Attack Mode:':<20} DISABLED (clean baseline)")
        
        # Self-healing info
        sh_cfg = self.config.get("self_healing", {})
        if sh_cfg.get("enabled", False):
            print(f"{'Self-Healing:':<20} ENABLED | "
                  f"DPS threshold: {sh_cfg.get('dps_threshold', 2.0)} | "
                  f"Recovery rounds: {sh_cfg.get('recovery_rounds', 3)}")
        else:
            print(f"{'Self-Healing:':<20} DISABLED")
        
        print("=" * 100)
    
    def _print_round_header(self, round_num: int, total_rounds: int):
        """Print round header."""
        print("\n" + "-" * 100)
        print(f"ROUND {round_num}/{total_rounds}")
        print("-" * 100)
    
    def _print_metrics(self, round_num: int, metrics: dict, dps_scores: dict, 
                       sh_state: str = "N/A", quarantined: List[int] = None):
        """Print real-time metrics for current round."""
        
        # Basic metrics
        acc = metrics.get("accuracy", 0.0)
        loss = metrics.get("loss", 0.0)
        
        # DPS scores
        avg_dps = np.mean(list(dps_scores.values())) if dps_scores else 0.0
        max_dps = max(dps_scores.values()) if dps_scores else 0.0
        suspicious = sum(1 for dps in dps_scores.values() if dps > 2.0) if dps_scores else 0
        
        # Status indicator
        if sh_state == "NORMAL":
            status_icon = "✅"
            status_color = "HEALTHY"
        elif sh_state in ["MONITOR", "RECOVERY", "VALIDATE"]:
            status_icon = "🔴"
            status_color = "ATTACK/RECOVERY"
        elif sh_state == "RESUME":
            status_icon = "🔄"
            status_color = "RESUMING"
        else:
            status_icon = "⚪"
            status_color = "UNKNOWN"
        
        # Print formatted output
        print(f"\n{status_icon} Round {round_num:2d} | State: {sh_state:12s} | {status_color}")
        print(f"   ├─ Accuracy:  {acc:6.3f}  {'(↑ Good)' if acc > 0.7 else '(↓ Poor)' if acc < 0.5 else ''}")
        print(f"   ├─ Loss:      {loss:6.3f}  {'(↓ Good)' if loss < 0.5 else '(↑ Poor)' if loss > 0.7 else ''}")
        print(f"   ├─ DPS:       Avg={avg_dps:5.2f}, Max={max_dps:5.2f}, Suspicious={suspicious}/{len(dps_scores) if dps_scores else 0}")
        
        if quarantined:
            print(f"   └─ Quarantined Clients: {quarantined}")
        else:
            print(f"   └─ Quarantined Clients: None")
    
    def _compute_dps_scores(self, client_updates: List[Tuple[int, List]]) -> Dict[int, float]:
        """Compute Dynamic Poisoning Scores for clients."""
        dps_scores = {}
        
        if not client_updates or len(client_updates) < 2:
            return dps_scores
        
        # Extract client IDs and parameters
        client_params = {}
        for cid, params in client_updates:
            client_params[cid] = params
        
        # Compute pairwise distances
        for cid1, params1 in client_params.items():
            distances = []
            for cid2, params2 in client_params.items():
                if cid1 != cid2:
                    # L2 distance between parameter vectors
                    dist = 0.0
                    for p1, p2 in zip(params1, params2):
                        dist += np.sum((p1 - p2) ** 2)
                    distances.append(np.sqrt(dist))
            
            # DPS = average distance to other clients
            dps_scores[cid1] = np.mean(distances) if distances else 0.0
        
        return dps_scores
    
    def run(self):
        """Run the integrated simulation."""
        self._print_header()
        
        # Step 1: Load and partition dataset
        print("\n[Step 1/5] Loading UCI Heart Disease dataset...")
        data_loader = HeartDiseaseDataLoader(
            dataset_id=self.config["dataset_id"],
            random_seed=self.config["random_seed"],
            test_split=self.config["test_split"]
        )
        
        federated_data = data_loader.get_federated_data(
            num_clients=self.config["num_clients_total"],
            iid=self.config["iid"]
        )
        
        client_datasets = federated_data["client_data"]
        test_data = federated_data["test_data"]
        self.config["input_dim"] = federated_data["input_dim"]
        print(f"   ✓ Dataset loaded: {federated_data['input_dim']} features, {len(test_data[0])} test samples")
        
        # Step 2: Initialize global model
        print("\n[Step 2/5] Initializing global model...")
        model = HeartDiseaseNet(
            input_dim=self.config["input_dim"],
            hidden_dim=self.config["hidden_dim"],
            output_dim=self.config["output_dim"]
        )
        initial_parameters = get_model_parameters(model)
        print(f"   ✓ Model initialized: {sum(p.size for p in initial_parameters)} parameters")
        
        # Step 3: Setup attack configuration
        print("\n[Step 3/5] Configuring attack simulation...")
        attack_cfg_raw = self.config.get("attack", {})
        attack_config = AttackConfig.from_dict(attack_cfg_raw)
        
        client_fn, ground_truth = get_client_fn_with_attacks(
            client_data=client_datasets,
            config=self.config,
            attack_config=attack_config,
        )
        
        if attack_config.enabled:
            mal_ids = [cid for cid, bad in ground_truth.items() if bad]
            print(f"   ✓ Attack enabled: {attack_config.attack_type} with malicious clients {mal_ids}")
        else:
            print(f"   ✓ Clean baseline (no attacks)")
        
        # Step 4: Initialize self-healing controller
        print("\n[Step 4/5] Initializing self-healing controller...")
        sh_config = self.config.get("self_healing", {})
        if sh_config.get("enabled", False):
            self.sh_controller = SelfHealingController(sh_config)
            print(f"   ✓ Self-healing enabled")
        else:
            self.sh_controller = None
            print(f"   ✓ Self-healing disabled")
        
        # Step 5: Setup strategy
        print("\n[Step 5/5] Configuring FedAvg strategy...")
        strategy_wrapper = FedAvgStrategy(
            test_data=test_data,
            config=self.config,
            fraction_fit=self.config["fraction_fit"],
            fraction_evaluate=self.config["fraction_evaluate"],
            min_fit_clients=self.config["min_fit_clients"],
            min_evaluate_clients=self.config["min_evaluate_clients"],
            min_available_clients=self.config["min_available_clients"]
        )
        strategy = strategy_wrapper.get_strategy()
        print(f"   ✓ Strategy configured: FedAvg")
        
        # Start simulation
        print("\n" + "=" * 100)
        print(" " * 35 + "SIMULATION STARTING")
        print("=" * 100)
        time.sleep(1)
        
        # Run simulation with custom monitoring
        self._run_monitored_simulation(
            client_fn=client_fn,
            strategy=strategy,
            test_data=test_data,
            model_template=model
        )
        
        # Print final summary
        self._print_summary()
    
    def _run_monitored_simulation(self, client_fn, strategy, test_data, model_template):
        """Run simulation with round-by-round monitoring."""
        
        num_rounds = self.config["num_rounds"]
        num_clients = self.config["num_clients_total"]
        clients_per_round = self.config["num_clients_per_round"]
        
        # Initialize global model
        global_params = get_model_parameters(model_template)
        
        for round_num in range(1, num_rounds + 1):
            self._print_round_header(round_num, num_rounds)
            
            # Select clients for this round
            selected_clients = np.random.choice(num_clients, clients_per_round, replace=False)
            print(f"Selected clients: {list(selected_clients)}")
            
            # Collect client updates
            client_updates = []
            for cid in selected_clients:
                client = client_fn(str(cid))
                
                # Client trains locally
                updated_params, num_samples, _ = client.fit(
                    parameters=global_params,
                    config={"round": round_num}
                )
                client_updates.append((int(cid), updated_params))
            
            print(f"Received {len(client_updates)} client updates")
            
            # Compute DPS scores
            dps_scores = self._compute_dps_scores(client_updates)
            
            # Aggregate parameters (simple FedAvg)
            all_params = [params for _, params in client_updates]
            candidate_params = []
            for i in range(len(all_params[0])):
                layer_params = [client_params[i] for client_params in all_params]
                avg_param = np.mean(layer_params, axis=0)
                candidate_params.append(avg_param)
            
            # Evaluate on test set
            set_model_parameters(model_template, candidate_params)
            X_test, y_test = test_data
            model_template.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X_test)
                y_tensor = torch.FloatTensor(y_test).unsqueeze(1)
                
                outputs = model_template(X_tensor)
                loss = torch.nn.functional.binary_cross_entropy(outputs, y_tensor)
                predictions = (outputs > 0.5).float()
                accuracy = (predictions == y_tensor).float().mean().item()
            
            metrics = {
                "accuracy": accuracy,
                "loss": loss.item()
            }
            
            # Apply self-healing if enabled
            sh_state = "N/A"
            quarantined = []
            
            if self.sh_controller:
                final_params, status_msg = self.sh_controller.update(
                    round_num=round_num,
                    candidate_params=candidate_params,
                    metrics=metrics,
                    dps_dict=dps_scores,
                    reputation={},
                    client_updates=client_updates
                )
                
                global_params = final_params if final_params is not None else candidate_params
                
                # Get status from controller
                status = self.sh_controller.get_status_summary()
                sh_state = status["state"]
                quarantined = [cid for cid in range(num_clients) 
                              if self.sh_controller.is_client_quarantined(cid)]
            else:
                global_params = candidate_params
                sh_state = "DISABLED"
            
            # Store history
            self.metrics_history.append(metrics)
            self.dps_history.append(dps_scores)
            self.state_history.append(sh_state)
            
            # Print real-time metrics
            self._print_metrics(round_num, metrics, dps_scores, sh_state, quarantined)
            
            # Small delay for readability
            time.sleep(0.3)
    
    def _print_summary(self):
        """Print final simulation summary."""
        print("\n" + "=" * 100)
        print(" " * 35 + "SIMULATION COMPLETE")
        print("=" * 100)
        
        if not self.metrics_history:
            print("No metrics collected!")
            return
        
        # Extract metrics
        accuracies = [m["accuracy"] for m in self.metrics_history]
        losses = [m["loss"] for m in self.metrics_history]
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   ├─ Initial Accuracy:  {accuracies[0]:6.3f}")
        print(f"   ├─ Final Accuracy:    {accuracies[-1]:6.3f}")
        print(f"   ├─ Improvement:       {accuracies[-1] - accuracies[0]:+6.3f}")
        print(f"   ├─ Best Accuracy:     {max(accuracies):6.3f} (Round {accuracies.index(max(accuracies)) + 1})")
        print(f"   └─ Worst Accuracy:    {min(accuracies):6.3f} (Round {accuracies.index(min(accuracies)) + 1})")
        
        print(f"\n📉 LOSS TRAJECTORY:")
        print(f"   ├─ Initial Loss:      {losses[0]:6.3f}")
        print(f"   ├─ Final Loss:        {losses[-1]:6.3f}")
        print(f"   └─ Reduction:         {losses[0] - losses[-1]:+6.3f}")
        
        # DPS analysis
        if self.dps_history:
            all_dps = [dps for round_dps in self.dps_history for dps in round_dps.values() if dps > 0]
            if all_dps:
                print(f"\n🔍 DPS ANALYSIS:")
                print(f"   ├─ Average DPS:       {np.mean(all_dps):6.3f}")
                print(f"   ├─ Max DPS:           {np.max(all_dps):6.3f}")
                print(f"   └─ Suspicious Count:  {sum(1 for dps in all_dps if dps > 2.0)}/{len(all_dps)}")
        
        # State transitions
        if self.sh_controller:
            state_counts = defaultdict(int)
            for state in self.state_history:
                state_counts[state] += 1
            
            print(f"\n🔄 SELF-HEALING ACTIVITY:")
            for state, count in sorted(state_counts.items()):
                print(f"   ├─ {state:12s}: {count:2d} rounds ({count/len(self.state_history)*100:5.1f}%)")
            
            status = self.sh_controller.get_status_summary()
            print(f"   └─ Recovery Attempts: {status.get('recovery_attempts', 0)}")
        
        # Round-by-round details
        print(f"\n📈 ROUND-BY-ROUND DETAILS:")
        print(f"   {'Round':>6} {'Accuracy':>10} {'Loss':>10} {'Avg DPS':>10} {'State':>12}")
        print(f"   " + "-" * 60)
        
        for i, (metrics, dps_dict, state) in enumerate(zip(
            self.metrics_history, self.dps_history, self.state_history), 1):
            avg_dps = np.mean(list(dps_dict.values())) if dps_dict else 0.0
            acc = metrics["accuracy"]
            loss = metrics["loss"]
            
            # Status indicator
            if state == "NORMAL":
                icon = "✅"
            elif state in ["MONITOR", "RECOVERY", "VALIDATE"]:
                icon = "🔴"
            elif state == "RESUME":
                icon = "🔄"
            else:
                icon = "⚪"
            
            print(f"   {icon} {i:4d} {acc:10.3f} {loss:10.3f} {avg_dps:10.3f} {state:>12}")
        
        print("\n" + "=" * 100)
        print("✅ Simulation completed successfully!")
        print("=" * 100)


def main():
    """Main entry point."""
    import sys
    
    # Check for config override
    config_path = "configs/sim_config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Set random seeds
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Run simulation
    sim = RealTimeSimulation(config_path)
    sim.run()


if __name__ == "__main__":
    main()
