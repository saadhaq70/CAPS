"""Run an actual local-data federated simulation with self-healing enabled."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from dashboard.simulator import DashboardSimulator


def main() -> None:
    with (PROJECT_ROOT / "configs" / "sim_config.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    run_config = {
        "num_clients": config["num_clients_total"],
        "num_rounds": config["num_rounds"],
        "random_seed": config["random_seed"],
        "enable_attack": config["attack"]["enabled"],
        "attack_type": config["attack"]["attack_type"],
        "enable_self_healing": True,
        "dps_threshold": config["self_healing"]["dps_threshold"],
        "recovery_rounds": config["self_healing"]["recovery_rounds"],
    }
    results = DashboardSimulator(run_config).run_full_simulation()
    for row in results["rounds"]:
        metrics = row["metrics"]
        print(
            f"Round {row['round']}: accuracy={metrics['accuracy']:.4f}, "
            f"loss={metrics['loss']:.4f}, state={row['state']}"
        )
    print(f"Dataset: {results['data']['source_file']}")
    print(f"Recovery attempts: {results['recovery_attempts']}")


if __name__ == "__main__":
    main()
