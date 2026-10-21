"""
Script to execute the complete Defense Comparison matrix:
4 Defenses × 4 Attacks = 16 experimental runs
Saves reproducible results to results/defense_comparison/
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from defenses.runner import ComparisonRunner, ExperimentConfig


def main():
    print("=" * 80)
    print("RUNNING COMPLETE DEFENSE COMPARISON MATRIX")
    print("Defenses: Multi-Krum | Trimmed Mean | FLTrust | ASH-FL")
    print("Attacks:  Label Flip | Sign Flip  | Scaling | Backdoor")
    print("=" * 80)

    start_time = time.time()
    config = ExperimentConfig(
        num_clients=5,
        num_rounds=3,
        local_epochs=3,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        scale_factor=50.0,
    )

    runner = ComparisonRunner(config)
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "defense_comparison")

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
