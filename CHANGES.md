# Recent Changes

## 2026-09-21: Detection & Dashboard Improvements

### Detection Sensitivity
- P signal more sensitive: acc threshold 0.08→0.05, loss 0.5→0.3
- DPS weights: P increased 0.23→0.27 for better label-flip detection
- Default threshold: 0.6→0.55 (more sensitive)
- Label-flip now triggers recovery reliably

### Dashboard
- Unified dashboard is now the only recommended entry point
- Old dashboards (app.py, dashboard_app.py) deprecated
- Added accuracy breakdown: Initial/Lowest/Final with recovery %
- Added aggregation weights table in Self-Healing tab

### Code
- AdaptiveStrategy wired into main.py (when self_healing.enabled=true)
- Config consistency verified across all components
- All thresholds flow correctly: UI → Simulator → HealthMonitor

### Docs
- Accuracy claims: "85-90%" → "78-88% (typical 80-85%)"
- Signal normalization formulas documented
- D=0 explanation clear (disabled for privacy)

### Files Modified
Core: dps_calculator.py, health_monitor.py, main.py, sim_config.yaml
Dashboard: unified_dashboard.py, explanations.py
Docs: README.md, SETUP.md, CHANGELOG.md


## 2026-09-21: Cleanup

- Moved all test files to tests/ folder
- Deleted 19 verbose MD files, kept only README.md, SETUP.md, CHANGELOG.md, CHANGES.md
- Updated paths in README.md

- Fixed imports in all test files (added sys.path.insert for tests/ folder)
- Fixed run_all_tests.sh to run from correct directory
