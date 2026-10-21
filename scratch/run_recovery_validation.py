"""
Validation script for ASH-FL Option C against original benchmark and 5-round persistence test.
Saves all outputs to results/recovery_validation/ and protects results/defense_comparison/.
"""

import os
import sys
import json
import hashlib
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from defenses.runner import ComparisonRunner, ExperimentConfig


def get_dir_hashes(directory: str) -> Dict[str, str]:
    hashes = {}
    if not os.path.exists(directory):
        return hashes
    for fname in sorted(os.listdir(directory)):
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                hashes[fname] = hashlib.sha256(f.read()).hexdigest()
    return hashes


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    official_dir = os.path.join(base_dir, "results", "defense_comparison")
    validation_dir = os.path.join(base_dir, "results", "recovery_validation")
    os.makedirs(validation_dir, exist_ok=True)

    print("=" * 80)
    print("STEP 1: PRE-RUN SHA256 INTEGRITY CHECK OF OFFICIAL RESULTS")
    print("=" * 80)
    pre_hashes = get_dir_hashes(official_dir)
    for fname, h in pre_hashes.items():
        print(f"  {fname}: {h}")

    print("\n" + "=" * 80)
    print("STEP 2: RUNNING 3-ROUND MATRIX (16 COMBINATIONS) TO results/recovery_validation/")
    print("=" * 80)
    config_3r = ExperimentConfig(
        num_clients=5,
        num_rounds=3,
        local_epochs=3,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        dataset_id=45,
        scale_factor=50.0,
    )

    runner_3r = ComparisonRunner(config_3r)
    start_time = time.time()
    matrix_results = runner_3r.run_full_matrix(
        output_dir=validation_dir,
        progress_callback=lambda atk, msg: print(f"  -> Running attack matrix: {atk.upper()}..."),
    )
    elapsed_3r = time.time() - start_time
    print(f"3-round matrix completed in {elapsed_3r:.2f}s")

    print("\n" + "=" * 80)
    print("STEP 3: RUNNING 5-ROUND PERSISTENCE DIAGNOSTIC TEST (LABEL FLIP)")
    print("=" * 80)
    config_5r = ExperimentConfig(
        num_clients=5,
        num_rounds=5,
        local_epochs=3,
        batch_size=16,
        learning_rate=0.01,
        random_seed=42,
        dataset_id=45,
        scale_factor=50.0,
    )
    runner_5r = ComparisonRunner(config_5r)
    diag_5r_result = runner_5r.run_comparison(
        attack_type="label_flip",
        defense_names=["Multi-Krum", "ASH-FL"],
        progress_callback=lambda r, tot, d: print(f"  -> Round {r}/{tot} for {d}"),
    )

    diag_5r_path = os.path.join(validation_dir, "diag_5rounds_label_flip.json")
    with open(diag_5r_path, "w", encoding="utf-8") as f:
        json.dump(diag_5r_result.to_dict(), f, indent=2)
    print(f"Saved 5-round persistence diagnostic to: {diag_5r_path}")

    print("\n" + "=" * 80)
    print("STEP 4: POST-RUN SHA256 INTEGRITY CHECK OF OFFICIAL RESULTS")
    print("=" * 80)
    post_hashes = get_dir_hashes(official_dir)
    mismatches = []
    for fname, h in pre_hashes.items():
        post_h = post_hashes.get(fname)
        status = "MATCH" if h == post_h else "MODIFIED!"
        print(f"  {fname}: {status} ({post_h})")
        if h != post_h:
            mismatches.append(fname)

    if mismatches:
        print(f"\nCRITICAL ERROR: Official benchmark files modified: {mismatches}")
        sys.exit(1)
    else:
        print("\nSUCCESS: All official benchmark files remained 100% UNTOUCHED.")

    print("\n" + "=" * 80)
    print("STEP 5: BASELINE DEFENSE INVARIANCE AUDIT")
    print("=" * 80)
    baseline_defenses = ["Multi-Krum", "Trimmed Mean", "FLTrust"]
    attacks = ["label_flip", "sign_flip", "scaling", "backdoor"]
    all_baselines_identical = True

    for atk in attacks:
        off_path = os.path.join(official_dir, f"{atk}.json")
        val_path = os.path.join(validation_dir, f"{atk}.json")
        with open(off_path, "r", encoding="utf-8") as f:
            off_data = json.load(f)
        with open(val_path, "r", encoding="utf-8") as f:
            val_data = json.load(f)

        print(f"\nAttack: {atk.upper()}")
        for dname in baseline_defenses:
            off_def = off_data["defense_results"][dname]
            val_def = val_data["defense_results"][dname]

            acc_match = off_def["final_accuracy"] == val_def["final_accuracy"]
            loss_match = abs(off_def["final_loss"] - val_def["final_loss"]) < 1e-6
            asr_match = off_def.get("backdoor_asr") == val_def.get("backdoor_asr")

            status = "IDENTICAL" if (acc_match and loss_match and asr_match) else "DIFFERENT"
            if status != "IDENTICAL":
                all_baselines_identical = False
            print(f"  {dname:15s}: {status} | Acc: {val_def['final_accuracy']:.1%} | Loss: {val_def['final_loss']:.4f} | ASR: {val_def.get('backdoor_asr')}")

    print(f"\nBaseline Invariance Status: {'PASSED (All Identical)' if all_baselines_identical else 'FAILED'}")


if __name__ == "__main__":
    main()
