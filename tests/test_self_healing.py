#!/usr/bin/env python3
"""
Quick test to verify self-healing triggers properly.
"""

import sys
sys.path.insert(0, '/Users/saadansari/CAPS')

from dashboard.simulator import DashboardSimulator

print("=" * 80)
print("SELF-HEALING TRIGGER TEST")
print("=" * 80)

config = {
    'num_clients': 5,
    'num_rounds': 10,
    'random_seed': 42,
    'enable_attack': True,
    'attack_type': 'scaling',
    'num_malicious': 2,
    'scale_factor': 50.0,  # Very aggressive attack
    'enable_self_healing': True,
    'dps_threshold': 0.6,  # FIXED: DPS is normalized [0,1]
    'recovery_rounds': 3
}

print("\nConfiguration:")
print(f"  - Clients: {config['num_clients']}")
print(f"  - Rounds: {config['num_rounds']}")
print(f"  - Attack: {config['attack_type']} (scale={config['scale_factor']})")
print(f"  - Malicious: {config['num_malicious']} clients")
print(f"  - Self-healing: ENABLED")
print(f"  - DPS threshold: {config['dps_threshold']}")

print("\nRunning simulation...")
print("-" * 80)

simulator = DashboardSimulator(config)
results = simulator.run_full_simulation()

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

# Check if self-healing triggered
states = [r['state'] for r in results['rounds']]
unique_states = set(states)

print(f"\nStates observed: {unique_states}")
print(f"Recovery attempts: {results['recovery_attempts']}")

# Print round-by-round state
print("\nRound-by-round:")
for r in results['rounds']:
    round_num = r['round']
    state = r['state']
    acc = r['metrics']['accuracy']
    max_dps = max(r['dps_scores'].values()) if r['dps_scores'] else 0.0
    quarantined = r['quarantined']
    
    marker = "🟢" if state == 'NORMAL' else "🔴"
    q_str = f" | Quarantined: {quarantined}" if quarantined else ""
    
    print(f"  {marker} Round {round_num}: {state:10s} | Acc: {acc:.3f} | Max DPS: {max_dps:.2f}{q_str}")

# Final verdict
if 'NORMAL' in unique_states and len(unique_states) == 1:
    print("\n❌ SELF-HEALING DID NOT TRIGGER")
    print("   Check thresholds or attack strength")
    sys.exit(1)
else:
    print("\n✅ SELF-HEALING TRIGGERED SUCCESSFULLY!")
    print(f"   States: {' → '.join([r['state'] for r in results['rounds'] if r['state'] != 'NORMAL'][:5])}")
    sys.exit(0)
