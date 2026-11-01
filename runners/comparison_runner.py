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
import yaml

# Ensure project root is available on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from defenses.runner import ComparisonRunner, ExperimentConfig


def parse_args():
    with open(os.path.join(PROJECT_ROOT, "configs", "sim_config.yaml"), encoding="utf-8") as stream:
        project_config = yaml.safe_load(stream)
    attack_config = project_config["attack"]
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
        default=int(project_config["random_seed"]),
        help="Random seed (defaults to configs/sim_config.yaml)",
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=int(project_config["num_clients_total"]),
        help="Total number of federated clients (defaults to configs/sim_config.yaml)",
    )
    parser.add_argument(
        "--num-rounds",
        type=int,
        default=int(project_config["num_rounds"]),
        help="Number of federated learning rounds (defaults to configs/sim_config.yaml)",
    )
    parser.add_argument(
        "--local-epochs",
        type=int,
        default=int(project_config["local_epochs"]),
        help="Number of local epochs per round (defaults to configs/sim_config.yaml)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(project_config["batch_size"]),
        help="Local training batch size (defaults to configs/sim_config.yaml)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=float(project_config["learning_rate"]),
        help="Client learning rate (defaults to configs/sim_config.yaml)",
    )
    parser.add_argument(
        "--hidden-dim",
        type=int,
        default=int(project_config["hidden_dim"]),
        help="First hidden-layer width",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=float(attack_config["scale_factor"]),
        help="Scaling factor for model replacement attack",
    )
    parser.add_argument(
        "--malicious-client-ids",
        type=int,
        nargs="+",
        default=list(attack_config["malicious_client_ids"]),
        help="Client IDs that receive the selected attack",
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
    print(f"Clients:       {args.num_clients} (Malicious IDs: {args.malicious_client_ids})")
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
        hidden_dim=args.hidden_dim,
        random_seed=args.seed,
        dataset_path=os.path.join(PROJECT_ROOT, project_config["dataset_path"]),
        test_split=float(project_config["test_split"]),
        iid=bool(project_config["iid"]),
        scale_factor=args.scale_factor,
        malicious_client_ids=args.malicious_client_ids,
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
    if args.all and os.path.exists(summary_csv):
        import pandas as pd
        df = pd.read_csv(summary_csv)
        print("\nSummary Table:")
        print(df.to_string(index=False))
    elif not args.all:
        print("\nFresh comparison summary:")
        print(res.to_dataframe().to_string(index=False))

    print(f"\nFiles in {args.output_dir}:")
    for fname in sorted(os.listdir(args.output_dir)):
        fpath = os.path.join(args.output_dir, fname)
        size_kb = os.path.getsize(fpath) / 1024.0
        print(f"  - {fname:<25} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
