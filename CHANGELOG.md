# Changelog

## Phase 2 - Complete ✅

**Added:**
- `attacks/` package — four attack types with shared `BaseAttack` / `AttackConfig` interface:
  - `label_flip.py` — flips source_label → target_label in local training data
  - `sign_flip.py`  — negates the model update delta (gradient reversal)
  - `scaling.py`    — amplifies the update delta by a configurable scale_factor
  - `backdoor.py`   — stamps a trigger pattern on a fraction of samples and forces a target label
- `attacks/malicious_client.py` — `MaliciousClient` extending `HeartDiseaseClient`; applies attack hooks inside `fit()` only
- `attacks/client_factory.py`   — `get_client_fn_with_attacks()` assigns malicious IDs and exposes `ground_truth: Dict[int, bool]` for Phase 3 scoring
- `attack_demo.py` — runs clean baseline + all four attack types back-to-back and prints accuracy-delta table

**Modified:**
- `configs/sim_config.yaml` — added `attack:` block (default `enabled: false`; Phase 1 behaviour unchanged)
- `main.py` — loads `AttackConfig`, uses `get_client_fn_with_attacks`, prints ground-truth IDs when attack is on

**Not changed:**
- `aggregation/strategy.py` FedAvg logic (zero modifications as per spec)
- `clients/client.py` / `clients/data_loader.py` (unchanged)

**Status:** Attack harness working; `python main.py` with `attack.enabled: false` is identical to Phase 1

---

## Phase 1 - Complete ✅

**Created:**
- FL simulator with FedAvg baseline
- UCI Heart Disease dataset integration (IID partitioning)
- PyTorch 3-layer neural network
- Flower simulation framework
- Config system (YAML)

**Files:**
- `main.py` - Main simulation
- `demo_quick.py` - Fast test
- `test_setup.py` - Verify install
- `clients/data_loader.py` - Dataset handling
- `clients/client.py` - Model + FL client
- `aggregation/strategy.py` - FedAvg
- `configs/sim_config.yaml` - Hyperparameters

**Status:** Working baseline, ready for Phase 2 security features

---

**Updates will be added here as changes are made**
