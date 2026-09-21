# Changelog

## Phase 5 - Unified Dashboard ✅ NEW

**Created single unified dashboard combining Cyber HUD design with real functionality.**

**File:** `unified_dashboard.py`  
**Launch:** `bash run_unified.sh`  
**Documentation:** `UNIFIED_DASHBOARD.md`

### What's New
- ✨ **Cyber HUD Design**: Orbitron fonts, neon glassmorphism, dark theme (from `app.py`)
- 🎯 **Real Functionality**: Actual DPS, attacks, self-healing (from `dashboard_app.py`)
- 🐛 **Fixed Recovery Counter Bug**: Now correctly tracks recovery attempts
  - **Problem**: Old code checked `if 'recovery' in status_msg.lower()` but status messages inconsistently contained "recovery"
  - **Result**: Counter almost always stayed at 0
  - **Solution**: Now reads directly from FSM controller state: `status.get('recovery_attempts', 0)`
- 📊 **Enhanced Visualizations**: All charts styled with consistent Cyber HUD theme
- 🎨 **Design System**: CSS variables, glassmorphism cards, color-coded badges

### Features
- Per-client attack configuration with quick presets
- Real-time DPS calculation (G, C, H, P, D signals)
- Shadow validation for P signal (tests updates on clean data)
- FSM-based self-healing with state timeline visualization
- Trust score evolution charts
- Radar charts for attack signature visualization
- Educational explanations tab

### Files Modified
- **New:** `unified_dashboard.py` - Main unified dashboard
- **New:** `run_unified.sh` - Launch script
- **New:** `UNIFIED_DASHBOARD.md` - Complete documentation
- **Fixed:** `dashboard/simulator.py` - Recovery counter bug fix (line 284-287)
- **Updated:** `README.md` - Points to unified dashboard

### Migration
- Old dashboards still work but are deprecated:
  - `app.py` - Beautiful but fake numbers
  - `dashboard_app.py` - Functional but plain UI and broken counter
- **Use `unified_dashboard.py` going forward** ✅

---

## Phase 4 - Dashboard ✅

Created interactive Streamlit web app for visualization.

**Files:** `dashboard_app.py`, `dashboard/*.py`, `run_dashboard.sh`  
**Launch:** `bash run_dashboard.sh`  
**Features:** 6 tabs (overview, performance, DPS deep dive, trust, self-healing, explanations), interactive controls, real-time charts  
**Known Issues:** Recovery counter broken (always shows 0) - **FIXED in Phase 5**

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
