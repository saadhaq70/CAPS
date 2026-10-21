"""
Comparison Runner CLI Entrypoint
Executes the Defense Comparison matrix (4 Defenses × 4 Attacks) or individual evaluations.

Usage:
    python -m runners.comparison_runner --all [--seed 42]
    python -m runners.comparison_runner --attack label_flip [--seed 42]
"""

import argparse
import os
import sys
import time

# Ensure project root is available on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from defenses.runner import ComparisonRunner, ExperimentConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run CAPS / ASH-FL Defense Comparison Matrix (Multi-Krum, Trimmed Mean, FLTrust, ASH-FL)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run the complete 4x4 matrix across all threat vectors (label_flip, sign_flip, scaling, backdoor)",
    )
    parser.add_argument(
        "--attack",
        type=str,
        default="label_flip",
        choices=["label_flip", "sign_flip", "scaling", "backdoor"],
        help="Single attack to evaluate if not running --all (default: label_flip)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for data partitioning and weight initialization (default: 42)",
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=5,
        help="Total number of federated clients (default: 5)",
    )
    parser.add_argument(
        "--num-rounds",
        type=int,
        default=3,
        help="Number of federated learning rounds (default: 3)",
    )
    parser.add_argument(
        "--local-epochs",
        type=int,
        default=3,
        help="Number of local epochs per round (default: 3)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Local training batch size (default: 16)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.01,
        help="Client SGD learning rate (default: 0.01)",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=50.0,
        help="Scaling factor for model replacement attack (default: 50.0)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "results", "defense_comparison"),
        help="Directory to save JSON results and comparison_summary.csv",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 80)
    print("CAPS / ASH-FL DEFENSE COMPARISON RUNNER")
    print("=" * 80)
    print(f"Seed:          {args.seed}")
    print(f"Clients:       {args.num_clients} (Malicious: Client 4)")
    print(f"Rounds:        {args.num_rounds}")
    print(f"Local Epochs:  {args.local_epochs}")
    print(f"Output Dir:    {args.output_dir}")
    print("=" * 80)

    config = ExperimentConfig(
        num_clients=args.num_clients,
        num_rounds=args.num_rounds,
        local_epochs=args.local_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        random_seed=args.seed,
        scale_factor=args.scale_factor,
    )

    runner = ComparisonRunner(config)
    os.makedirs(args.output_dir, exist_ok=True)
    start_time = time.time()

    if args.all:
        print("\nExecuting Complete 4x4 Matrix (Multi-Krum | Trimmed Mean | FLTrust | ASH-FL)...")
        matrix_results = runner.run_full_matrix(
            output_dir=args.output_dir,
            progress_callback=lambda atk, msg: print(f"\n>>> Running attack matrix: {atk.upper()}..."),
        )
    else:
        print(f"\nExecuting single attack evaluation: {args.attack.upper()}...")
        res = runner.run_comparison(attack_type=args.attack)
        res_file = os.path.join(args.output_dir, f"{args.attack}.json")
        res.save_json(res_file)
        print(f"Saved: {res_file}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"EXECUTION COMPLETE in {elapsed:.1f}s")
    print("=" * 80)

    summary_csv = os.path.join(args.output_dir, "comparison_summary.csv")
    if os.path.exists(summary_csv):
        import pandas as pd
        df = pd.read_csv(summary_csv)
        print("\nSummary Table:")
        print(df.to_string(index=False))

    print(f"\nFiles in {args.output_dir}:")
    for fname in sorted(os.listdir(args.output_dir)):
        fpath = os.path.join(args.output_dir, fname)
        size_kb = os.path.getsize(fpath) / 1024.0
        print(f"  - {fname:<25} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
