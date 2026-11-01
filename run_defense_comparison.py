"""
Script to execute the complete Defense Comparison matrix:
4 Defenses × 4 Attacks = 16 experimental runs
Saves reproducible results to results/defense_comparison/
"""

import os
import sys
import time
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from defenses.runner import ComparisonRunner, ExperimentConfig


def main():
    print("=" * 80)
    print("RUNNING COMPLETE DEFENSE COMPARISON MATRIX")
    print("Defenses: Multi-Krum | Trimmed Mean | FLTrust | ASH-FL")
    print("Attacks:  Label Flip | Sign Flip  | Scaling | Backdoor")
    print("=" * 80)

    start_time = time.time()
    project_root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(project_root, "configs", "sim_config.yaml"), encoding="utf-8") as stream:
        project_config = yaml.safe_load(stream)
    attack_config = project_config["attack"]
    config = ExperimentConfig(
        num_clients=project_config["num_clients_total"],
        num_rounds=project_config["num_rounds"],
        local_epochs=project_config["local_epochs"],
        batch_size=project_config["batch_size"],
        learning_rate=project_config["learning_rate"],
        optimizer_type=project_config["optimizer_type"],
        random_seed=project_config["random_seed"],
        dataset_path=os.path.join(project_root, project_config["dataset_path"]),
        test_split=project_config["test_split"],
        iid=project_config["iid"],
        hidden_dim=project_config["hidden_dim"],
        scale_factor=attack_config["scale_factor"],
        malicious_client_ids=list(attack_config["malicious_client_ids"]),
    )

    runner = ComparisonRunner(config)
    output_dir = os.path.join(project_root, "results", "defense_comparison")

    print(f"\nResults will be saved to: {output_dir}\n")

    matrix_results = runner.run_full_matrix(
        output_dir=output_dir,
        progress_callback=lambda atk, msg: print(f"\n>>> Running attack matrix: {atk.upper()}..."),
    )

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"EXPERIMENT MATRIX COMPLETE in {elapsed:.1f}s")
    print("=" * 80)

    summary_csv = os.path.join(output_dir, "comparison_summary.csv")
    if os.path.exists(summary_csv):
        import pandas as pd
        df = pd.read_csv(summary_csv)
        print("\nSummary Table:")
        print(df.to_string(index=False))

    print(f"\nGenerated files in {output_dir}:")
    for f in os.listdir(output_dir):
        print(f"  - {f}")


if __name__ == "__main__":
    main()
