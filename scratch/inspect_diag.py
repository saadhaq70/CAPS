import json

with open("results/recovery_validation/diag_5rounds_label_flip.json") as f:
    d = json.load(f)

ash = d["defense_results"]["ASH-FL"]
krum = d["defense_results"]["Multi-Krum"]

print("=== 5-ROUND DIAGNOSTIC COMPARISON: LABEL FLIP ===")
print("Multi-Krum:")
print(f"  Final Accuracy: {krum['final_accuracy']:.1%}")
print(f"  Final Loss: {krum['final_loss']:.4f}")
print(f"  Per-round Accuracy: {[round(x, 4) for x in krum['per_round_accuracy']]}")
print(f"  Per-round Loss: {[round(x, 4) for x in krum['per_round_loss']]}")

print("\nASH-FL:")
print(f"  Final Accuracy: {ash['final_accuracy']:.1%}")
print(f"  Final Loss: {ash['final_loss']:.4f}")
print(f"  Per-round Accuracy: {[round(x, 4) for x in ash['per_round_accuracy']]}")
print(f"  Per-round Loss: {[round(x, 4) for x in ash['per_round_loss']]}")
print(f"  Recovery metrics: {ash['recovery_metrics']}")

print("\nASH-FL Per-Round Telemetry:")
for i, m in enumerate(ash["per_round_defense_metrics"]):
    print(f"\nRound {i+1}:")
    print(f"  FSM State: {m['fsm_state']}")
    print(f"  Quarantined: {m['quarantined_clients']}")
    print(f"  Status msg: {m['status_message']}")
    print(f"  Checkpoint count: {m['checkpoint_count']}")
    dps_str = {int(k): round(v, 3) for k, v in m["dps_scores"].items()}
    trust_str = {int(k): round(v, 3) for k, v in m["trust_scores"].items()}
    weights_str = {int(k): round(v, 3) for k, v in m["aggregation_weights"].items()}
    print(f"  DPS: {dps_str}")
    print(f"  Trust: {trust_str}")
    print(f"  Weights: {weights_str}")
