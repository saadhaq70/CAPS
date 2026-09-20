# Changelog

## Phase 4 - Dashboard ✅

Created interactive Streamlit web app for visualization.

**Files:** `dashboard_app.py`, `dashboard/*.py`, `run_dashboard.sh`  
**Launch:** `bash run_dashboard.sh`  
**Features:** 6 tabs (overview, performance, DPS deep dive, trust, self-healing, explanations), interactive controls, real-time charts  

---

## Phase 3 - Self-Healing ✅

Added automatic attack detection and recovery system.

**Files:** `recovery/health_monitor.py`, `recovery/checkpoint_manager.py`, `recovery/self_heal.py`  
**Tests:** `test_phase3.py`, `test_comprehensive.py`, `test_integration.py` (20/20 passed)  
**Features:** FSM controller (NORMAL/MONITOR/RECOVERY/VALIDATE/RESUME), health monitoring, checkpoint restore, client quarantine  

---

## Phase 2 - Attacks ✅

Added 4 attack types with malicious client injection.

**Files:** `attacks/*.py`, `attack_demo.py`  
**Attacks:** label_flip, sign_flip, scaling, backdoor  
**Config:** `attack:` block in `sim_config.yaml` (disabled by default)  

---

## Phase 1 - Baseline ✅

Created FL simulator with FedAvg on UCI Heart Disease dataset.

**Files:** `main.py`, `clients/*.py`, `aggregation/strategy.py`, `configs/sim_config.yaml`  
**Framework:** Flower + PyTorch  
**Dataset:** UCI Heart Disease (297 samples, 13 features, binary classification)  
