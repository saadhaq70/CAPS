# CAPS // ASH-FL Unified Dashboard

## Overview

The **unified dashboard** (`unified_dashboard.py`) combines:
- ✨ Beautiful **Cyber HUD design** from `app.py` (Orbitron fonts, neon glassmorphism, dark theme)
- 🎯 **Real functionality** from `dashboard_app.py` (actual DPS, attacks, self-healing)
- 🐛 **Fixed recovery counter bug** (was always 0, now tracks correctly)

This is now the **single dashboard** you need to run ASH-FL simulations.

---

## Quick Start

### Run the Dashboard

```bash
# Option 1: Use the launch script
bash run_unified.sh

# Option 2: Direct streamlit command
streamlit run unified_dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

---

## Features

### 🎨 Cyber HUD Design
- **Fonts**: Orbitron (headers), Space Grotesk (body), JetBrains Mono (code)
- **Colors**: Neon cyan (#00f0ff), neon green (#00ff9d), neon purple (#9d4edd)
- **Effects**: Glassmorphism cards, glowing borders, smooth animations
- **Theme**: Dark background with radial gradient

### 🔍 Real Detection
- **DPS Calculation**: Real-time G, C, H, P, D scores
- **Shadow Validation**: P signal uses actual model evaluation
- **Per-Client Analysis**: Individual signal breakdown
- **Radar Charts**: Visual representation of attack signatures

### 🎯 Attack Configuration
- **Per-Client Assignment**: Configure attacks for each client individually
- **4 Attack Types**: Scaling, Label-Flip, Sign-Flip, Backdoor
- **Quick Presets**: "2 Scaling", "2 Label-Flip", "Mixed Attacks", "All Malicious"
- **Configurable Intensity**: Adjust scaling factor (1-100)

### 🛡️ Self-Healing
- **FSM-Based Recovery**: NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME
- **Automatic Detection**: Triggers when DPS > threshold
- **Client Quarantine**: Reduces malicious client weight to 0.1×
- **Checkpoint Restoration**: Reverts to last trusted model state
- **Recovery Tracking**: **Fixed bug** - now correctly counts recovery attempts

---

## Critical Bug Fix

### The Problem
In the original `dashboard_app.py`, the recovery counter was broken:

```python
# OLD CODE (BROKEN)
if 'recovery' in status_msg.lower():
    self.results['recovery_attempts'] += 1
```

This checked if the word "recovery" appeared in status messages, but:
- Status messages like "Restored checkpoint from round 5" don't contain "recovery"
- Status messages like "State: RECOVERY | Quarantined: [0, 1]" do, but inconsistently
- Result: Counter almost always stayed at 0

### The Solution
Now tracks recovery attempts directly from the FSM controller state:

```python
# NEW CODE (FIXED)
# Track recovery attempts directly from FSM state, not status message parsing
recovery_attempts_from_fsm = status.get('recovery_attempts', 0)
if recovery_attempts_from_fsm > self.results['recovery_attempts']:
    self.results['recovery_attempts'] = recovery_attempts_from_fsm
```

The FSM controller (`recovery/self_heal.py`) already tracks `recovery_attempt_count` internally when `_initiate_recovery()` is called. We now read this value directly instead of parsing strings.

---

## Usage Guide

### 1. Configure Simulation

Use the **sidebar** to configure your simulation:

#### Basic Parameters
- **Total Clients (K)**: 3-10 clients (default: 5)
- **Federation Rounds**: 5-20 rounds (default: 8)
- **Random Seed**: For reproducibility (default: 42)

#### Attack Configuration
- **Enable Attacks**: Toggle on/off
- **Quick Preset**: Choose from predefined attack scenarios
- **Per-Client Custom**: Assign specific attacks to individual clients
- **Scaling Factor**: Adjust attack intensity (1-100, default: 50)

#### Self-Healing
- **Enable Self-Healing**: Toggle FSM-based recovery
- **DPS Threshold**: 0.3-1.0 (default: 0.6)
  - 0.6 = balanced (catches most attacks, few false positives)
  - 0.7 = strict (only flags clear attacks)
  - 0.5 = sensitive (catches subtle attacks, may flag honest outliers)
- **Recovery Rounds**: How many rounds to retrain (default: 3)

### 2. Run Simulation

Click **🚀 EXECUTE** in the sidebar to start the simulation.

### 3. Explore Results

The dashboard has **4 tabs**:

#### 📊 OVERVIEW
- **Metrics Ribbon**: Final accuracy, loss, detection rate, recovery attempts
- **Charts**: Accuracy trajectory and loss convergence over rounds
- **Ground Truth Table**: Shows which clients are malicious, their attack types, and detection status

#### 🔍 DPS ANALYSIS
- **Signal Breakdown Table**: G, C, H, P, D scores for each client
- **Radar Charts**: Visual representation of malicious client signatures
- **Detection Status**: Which clients were flagged (DPS > threshold)

#### 🛡️ SELF-HEALING
- **FSM State Timeline**: Shows state transitions (NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME)
- **Trust Evolution Chart**: How client trust scores change over time
- **Recovery Summary**: Total attempts, checkpoints created, final state

#### 📚 EXPLANATIONS
- **What is DPS?**: Explanation of the composite score
- **Signal Details**: Deep dive into G, C, H, P, D
- **Trust & Reputation**: How trust scores work
- **Self-Healing FSM**: State machine explanation
- **Configuration Tips**: Tuning guidelines

---

## Understanding the Results

### Metrics Ribbon (Top of Page)

**Final Accuracy**
- Shows final global model accuracy
- Delta shows improvement from initial round
- Green = improved, Red = degraded

**Final Loss**
- Cross-entropy loss on test set
- Delta shows change from initial round
- Green = decreased (good), Red = increased (bad)

**Malicious Nodes**
- X/Y format: X malicious out of Y total clients
- Based on ground truth (attack configuration)

**Detection Rate**
- Percentage of malicious clients detected
- Based on DPS > threshold in final round
- 100% = perfect detection

**Recovery Attempts**
- **NOW WORKS CORRECTLY** ✅
- Shows how many times FSM triggered recovery
- 0 = no attacks detected or self-healing disabled
- 1+ = system detected and responded to attacks

### Ground Truth Table

**Status Column**
- 🔴 MALICIOUS = Client has attack configured
- ✅ HONEST = Client is behaving normally

**Attack Type Column**
- None = Honest client
- Scaling/Label-Flip/Sign-Flip/Backdoor = Attack type assigned

**Detection Column**
- ✅ DETECTED = Malicious client correctly flagged (DPS > threshold)
- ❌ MISSED = Malicious client not detected (DPS < threshold)
- ✅ CORRECT = Honest client not flagged (true negative)

### DPS Signal Breakdown

**G (Gradient Deviation)**
- Measures distance from median update
- High = update magnitude is unusual
- Catches: Scaling attacks

**C (Cosine Disagreement)**
- Measures angular distance from consensus
- High = update points in wrong direction
- Catches: Sign-flip attacks

**H (History Deviation)**
- Compares current behavior to client's history
- High = sudden change in behavior
- Catches: Time-delayed attacks

**P (Performance Impact)**
- Shadow validation: tests update on clean data
- High = update hurts model accuracy or spikes loss
- Catches: Label-flip, backdoor, all attacks eventually

**D (Data Quality)**
- **Always 0.0** (disabled for privacy)
- Would require access to local data (violates FL)
- Weight redistributed to other signals

### FSM States

**NORMAL**
- Healthy operation
- Monitoring metrics and DPS
- Creating checkpoints

**MONITOR**
- Degradation detected
- Confirming it's not noise
- Lasts 1 round

**RECOVERY**
- Active recovery in progress
- Checkpoint restored
- Quarantine active (malicious clients get 0.1× weight)
- Lasts N rounds (default: 3)

**VALIDATE**
- Testing if recovery worked
- Compares accuracy to pre-recovery baseline
- If improved → RESUME
- If failed → expand quarantine and retry

**RESUME**
- Recovery successful
- Transitioning back to normal
- Quarantine still active for a few rounds

---

## Comparison with Old Dashboards

### vs. `app.py` (Cyber HUD)
| Feature | app.py | unified_dashboard.py |
|---------|--------|---------------------|
| Design | ✅ Cyber HUD | ✅ Cyber HUD (same) |
| DPS Scores | ❌ Fake/random | ✅ Real calculation |
| Attacks | ❌ Not implemented | ✅ 4 attack types |
| Self-Healing | ❌ Visual only | ✅ Real FSM |
| Recovery Counter | ❌ N/A | ✅ Fixed |

### vs. `dashboard_app.py` (Functional)
| Feature | dashboard_app.py | unified_dashboard.py |
|---------|------------------|---------------------|
| Design | ❌ Plain Streamlit | ✅ Cyber HUD |
| DPS Scores | ✅ Real | ✅ Real (same) |
| Attacks | ✅ Per-client config | ✅ Per-client config (same) |
| Self-Healing | ✅ Real FSM | ✅ Real FSM (same) |
| Recovery Counter | ❌ Broken (always 0) | ✅ Fixed |

---

## Testing the Fix

### Verify Recovery Counter Works

1. **Configure attack scenario:**
   - Enable Attacks: ✅
   - Quick Preset: "2 Scaling"
   - Scaling Factor: 50
   - Enable Self-Healing: ✅
   - DPS Threshold: 0.6

2. **Run simulation:**
   - Click **🚀 EXECUTE**
   - Wait for completion

3. **Check recovery counter:**
   - Look at **Recovery Attempts** metric in top ribbon
   - Should show **1 or more** (not 0!)
   - Also visible in Self-Healing tab → Recovery Summary

4. **Cross-check with timeline:**
   - Go to **🛡️ SELF-HEALING** tab
   - Check **State Machine Timeline** table
   - Count rounds where FSM State = "RECOVERY"
   - Should match the recovery attempts counter

### Expected Behavior

**With Scaling Attack (scale=50, 2 malicious clients):**
- DPS for malicious clients: ~0.7-0.9
- FSM should trigger: **YES** (DPS > 0.6)
- Recovery attempts: **1-2**
- Final state: RESUME or NORMAL

**With Label-Flip Attack (2 malicious clients):**
- DPS for malicious clients: ~0.5-0.7 (improved P signal helps)
- FSM should trigger: **YES** (DPS > 0.6)
- Recovery attempts: **1-2**
- Final state: RESUME or NORMAL

**With No Attacks (all honest):**
- All DPS: < 0.3
- FSM should trigger: **NO**
- Recovery attempts: **0**
- Final state: NORMAL

---

## Architecture

### Code Structure

```
unified_dashboard.py
├── Imports (streamlit, plotly, simulator, visualizations)
├── CSS Styling (Cyber HUD design)
├── Session State (simulation_run, simulation_results)
├── render_sidebar() → Configuration panel
├── render_header() → Top HUD header
├── render_welcome_screen() → Pre-simulation view
├── render_metrics_ribbon() → Top 5 metrics (FIXED recovery counter)
├── render_overview_tab() → Charts and ground truth
├── render_dps_tab() → Signal analysis and radar
├── render_selfhealing_tab() → FSM timeline and trust
├── render_explanations_tab() → Educational content
└── main() → Application entry point
```

### Key Design Decisions

**CSS Variables**
- Defined once in `:root` for consistency
- `--neon-cyan`, `--neon-green`, `--neon-purple`, `--neon-red`
- Easy to change color scheme

**Glassmorphism Cards**
- `.cyber-card` class with backdrop blur
- Glowing cyan accent line (::before pseudo-element)
- Used consistently throughout

**Badges**
- `.cyber-badge`, `.cyber-badge-green`, `.cyber-badge-purple`, `.cyber-badge-red`
- Color-coded for different information types
- Monospace font (JetBrains Mono) for technical feel

**Tab Styling**
- Custom CSS for Streamlit tabs
- Active tab: cyan glow effect
- Inactive tab: muted gray

**Recovery Counter Fix**
- Reads directly from FSM controller state
- `status.get('recovery_attempts', 0)` from `get_status_summary()`
- No string parsing, no false negatives

---

## Troubleshooting

### Recovery Counter Still Shows 0

**Possible causes:**

1. **Self-healing disabled**
   - Check: Sidebar → "Enable Self-Healing" is checked
   - Solution: Enable it

2. **No attacks detected**
   - Check: DPS scores in DPS ANALYSIS tab
   - If all DPS < threshold → no trigger
   - Solution: Increase attack intensity or lower threshold

3. **Attack too subtle**
   - Check: Attack type and parameters
   - Label-flip at low flip rate may not trigger
   - Solution: Use scaling attack (scale=50) for guaranteed trigger

4. **Bug not fixed**
   - Check: You're running `unified_dashboard.py`, not `dashboard_app.py`
   - Solution: Use `bash run_unified.sh`

### DPS Not Showing

**Possible causes:**

1. **Module import error**
   - Check terminal for import errors
   - Solution: Ensure all dependencies installed

2. **Validation data missing**
   - Check: P signal shows 0.0 for all clients
   - Solution: Check data loader setup

### UI Doesn't Look Cyber

**Possible causes:**

1. **CSS not loading**
   - Check: Streamlit version >= 1.28
   - Solution: `pip install --upgrade streamlit`

2. **Font loading failed**
   - Check: Internet connection (Google Fonts CDN)
   - Solution: Fonts will fallback to system fonts

---

## Future Enhancements

Potential improvements for future versions:

### Functionality
- [ ] Step-by-step mode (advance round-by-round)
- [ ] Export results to JSON/CSV
- [ ] Compare multiple simulation runs
- [ ] Real-time streaming mode (watch training live)

### Visualization
- [ ] 3D network topology graph
- [ ] Animated state transitions
- [ ] Heatmap of DPS over time
- [ ] Client contribution breakdown

### Attacks
- [ ] Backdoor attack configuration (trigger patterns)
- [ ] Adaptive attacks (change behavior over time)
- [ ] Collusion between malicious clients

### Self-Healing
- [ ] Configurable FSM thresholds
- [ ] Multiple recovery strategies
- [ ] Automatic parameter tuning

---

## Credits

**Design Inspiration**: khaledoghli.com (Cyber HUD aesthetic)

**Fonts**:
- Orbitron (Google Fonts) - Headers
- Space Grotesk (Google Fonts) - Body
- JetBrains Mono (Google Fonts) - Code

**Framework**: Streamlit + Plotly

**Authors**: ASH-FL Team

---

## Changelog

### v2.0 - Unified Dashboard
- ✨ Combined Cyber HUD design with real functionality
- 🐛 Fixed recovery counter bug (was always 0)
- 🎨 Full glassmorphism styling
- 📊 Enhanced visualizations with consistent theme
- 🚀 Single launch script

### v1.2 - Dashboard App
- ✅ Real DPS calculation (G, C, H, P, D)
- ✅ Per-client attack configuration
- ✅ FSM-based self-healing
- ❌ Recovery counter broken
- ❌ Plain UI

### v1.0 - Cyber HUD (Visual Demo)
- ✨ Beautiful design
- ❌ Fake numbers
- ❌ No real functionality

---

## License

See main project LICENSE file.
