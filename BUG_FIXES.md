# Bug Fixes Applied

## Issue 1: KeyError 'G' in create_dps_radar

**Error:**
```
KeyError: 'G'
File "/Users/saadansari/CAPS/dashboard/visualizations.py", line 112
values = [signal_scores['G'], signal_scores['C'], ...]
```

**Root Cause:**
The `create_dps_radar` function had incorrect signature. It expected a `signal_scores` dictionary as first parameter, but was being called with `results` and `client_id`.

**Fix Applied:**
Changed function signature in `dashboard/visualizations.py`:

```python
# BEFORE (broken)
def create_dps_radar(signal_scores: Dict[str, float], is_malicious: bool = False) -> go.Figure:
    categories = [...]
    values = [signal_scores['G'], ...]  # ❌ KeyError here

# AFTER (fixed)
def create_dps_radar(results: Dict, client_id: int) -> go.Figure:
    """Extract scores from results for specific client"""
    final_round = results['rounds'][-1]
    is_malicious = results['ground_truth'].get(client_id, False)
    
    signal_scores = {
        'G': final_round.get('G_scores', {}).get(client_id, 0.0),
        'C': final_round.get('C_scores', {}).get(client_id, 0.0),
        'H': final_round.get('H_scores', {}).get(client_id, 0.0),
        'P': final_round.get('P_scores', {}).get(client_id, 0.0),
        'D': final_round.get('D_scores', {}).get(client_id, 0.0)
    }
    
    values = [signal_scores['G'], ...]  # ✅ Works now
```

**Files Modified:**
- `dashboard/visualizations.py` (lines 95-113)

---

## Issue 2: Inconsistent Key Names for FSM State

**Error:**
FSM state and quarantine data not displaying correctly in Self-Healing tab.

**Root Cause:**
Simulator stored FSM state with key name `'state'` but unified dashboard was looking for `'fsm_state'`. Same for quarantine: simulator uses `'quarantined'`, dashboard looked for `'quarantined_clients'`.

**Fix Applied:**
Updated key names in `unified_dashboard.py` to match simulator:

```python
# BEFORE (broken)
state = round_info.get('fsm_state', 'NORMAL')  # ❌ Wrong key
quarantined = round_info.get('quarantined_clients', [])  # ❌ Wrong key

# AFTER (fixed)
state = round_info.get('state', 'NORMAL')  # ✅ Correct key
quarantined = round_info.get('quarantined', [])  # ✅ Correct key
```

Also fixed final state retrieval:
```python
# BEFORE
final_state = results['rounds'][-1].get('fsm_state', 'UNKNOWN')  # ❌ Wrong key

# AFTER
final_state = results['rounds'][-1].get('state', 'UNKNOWN')  # ✅ Correct key
```

**Files Modified:**
- `unified_dashboard.py` (lines 628-630, 691)

---

## Verification

### How to Test

1. **Run unified dashboard:**
   ```bash
   bash run_unified.sh
   ```

2. **Configure simulation:**
   - Quick Preset: "Mixed Attacks"
   - Enable Self-Healing: ✅
   - DPS Threshold: 0.6

3. **Click EXECUTE**

4. **Check DPS Analysis tab:**
   - Should show radar charts for malicious clients
   - No KeyError should occur

5. **Check Self-Healing tab:**
   - FSM State Timeline should show correct states
   - Quarantined clients should be listed

### Expected Behavior After Fix

**DPS Analysis Tab:**
- ✅ Radar charts display correctly
- ✅ Shows G, C, H, P, D signals for each malicious client
- ✅ No KeyError exceptions

**Self-Healing Tab:**
- ✅ FSM timeline shows actual states (NORMAL, MONITOR, RECOVERY, etc.)
- ✅ Quarantined clients list populated correctly
- ✅ Final state displays in Recovery Summary

---

## Data Flow

### Simulator → Results Structure

```python
# dashboard/simulator.py (line 340-353)
round_result = {
    'round': round_num,
    'metrics': metrics,
    'dps_scores': dps_scores,
    'trust_scores': trust_scores,
    'aggregation_weights': aggregation_weights,
    'selected_clients': list(selected_clients),
    'state': state,                    # ← FSM state key
    'quarantined': quarantined,         # ← Quarantine key
    'G_scores': self.dps_calculator.last_G_scores.copy(),
    'C_scores': self.dps_calculator.last_C_scores.copy(),
    'H_scores': self.dps_calculator.last_H_scores.copy(),
    'P_scores': self.dps_calculator.last_P_scores.copy(),
    'D_scores': self.dps_calculator.last_D_scores.copy()
}
```

### Dashboard → Accessing Data

```python
# unified_dashboard.py
def render_dps_tab(results, dps_threshold):
    final_round = results['rounds'][-1]
    
    # Extract individual signal scores
    G = final_round.get('G_scores', {}).get(cid, 0)  # ✅ Correct
    C = final_round.get('C_scores', {}).get(cid, 0)  # ✅ Correct
    H = final_round.get('H_scores', {}).get(cid, 0)  # ✅ Correct
    P = final_round.get('P_scores', {}).get(cid, 0)  # ✅ Correct
    D = final_round.get('D_scores', {}).get(cid, 0)  # ✅ Correct

def render_selfhealing_tab(results):
    for round_info in results['rounds']:
        state = round_info.get('state', 'NORMAL')       # ✅ Correct key
        quarantined = round_info.get('quarantined', []) # ✅ Correct key
```

---

## Additional Notes

### PyTorch Warning (Non-Critical)

The warning about `torch.classes` can be safely ignored:
```
RuntimeError: Tried to instantiate class '__path__._path', but it does not exist!
```

This is a known issue with PyTorch and Streamlit's file watcher. It doesn't affect functionality.

**To suppress (optional):**
```bash
export PYTHONWARNINGS="ignore"
bash run_unified.sh
```

Or upgrade Streamlit:
```bash
pip install --upgrade streamlit
```

---

## Summary

**Total Bugs Fixed:** 2

1. ✅ **KeyError 'G'** - Fixed function signature in `visualizations.py`
2. ✅ **Wrong key names** - Fixed `'fsm_state'` → `'state'` and `'quarantined_clients'` → `'quarantined'`

**Files Modified:** 2
- `dashboard/visualizations.py`
- `unified_dashboard.py`

**Status:** All critical bugs resolved. Dashboard should now run without errors. ✅
