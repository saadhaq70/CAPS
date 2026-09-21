# Quick Reference Card

## 🚀 Launch Unified Dashboard

```bash
cd /Users/saadansari/CAPS
bash run_unified.sh
```

Opens at: `http://localhost:8501`

---

## ⚙️ Quick Configuration

### Recommended Test Setup

```
Sidebar Settings:
├── Total Clients: 5
├── Rounds: 8
├── Random Seed: 42
├── Enable Attacks: ✅
├── Quick Preset: "2 Scaling"
├── Scaling Factor: 50
├── Enable Self-Healing: ✅
└── DPS Threshold: 0.6
```

Click: 🚀 EXECUTE

---

## 📊 Reading Results

### Top Metrics Ribbon

| Metric | What It Shows | Good Value |
|--------|---------------|------------|
| **Final Accuracy** | Model accuracy | >80% |
| **Final Loss** | Cross-entropy loss | <0.4 |
| **Malicious Nodes** | X/Y attackers | Depends on config |
| **Detection Rate** | % caught | >80% |
| **Recovery Attempts** | FSM triggers | 1-2 (if attack strong) |

### Tab Navigation

- **📊 OVERVIEW**: Accuracy/loss charts, ground truth table
- **🔍 DPS ANALYSIS**: Signal breakdown (G,C,H,P,D), radar charts
- **🛡️ SELF-HEALING**: FSM timeline, trust evolution
- **📚 EXPLANATIONS**: Learn about DPS, signals, self-healing

---

## 🎯 Attack Presets

| Preset | Malicious | Attack Types | Expected DPS | Triggers? |
|--------|-----------|--------------|--------------|-----------|
| **2 Scaling** | 2/5 | Scaling ×50 | 0.7-0.9 | ✅ Yes |
| **2 Label-Flip** | 2/5 | Label-Flip | 0.5-0.7 | ✅ Yes |
| **Mixed Attacks** | 3/5 | Scaling + Label + Sign | 0.6-0.8 | ✅ Yes |
| **All Malicious** | 5/5 | Scaling ×50 | 0.8-1.0 | ✅ Yes |
| **(None)** | 0/5 | None | <0.3 | ❌ No |

---

## 🔍 DPS Signals Cheat Sheet

| Signal | Measures | Catches | Normal Range | Suspicious |
|--------|----------|---------|--------------|------------|
| **G** | Gradient deviation | Scaling | <0.3 | >0.6 |
| **C** | Cosine disagreement | Sign-flip | <0.2 | >0.5 |
| **H** | History change | Time-delayed | <0.3 | >0.6 |
| **P** | Performance impact | All attacks | <0.2 | >0.5 |
| **D** | Data quality | (disabled) | 0.0 | 0.0 |

**DPS Formula**: `0.30×G + 0.27×C + 0.20×H + 0.23×P + 0.00×D`

**Threshold**: 
- 0.6 = Balanced (default)
- 0.7 = Strict (fewer false positives)
- 0.5 = Sensitive (catches subtle attacks)

---

## 🛡️ FSM States

```
NORMAL → MONITOR → RECOVERY → VALIDATE → RESUME → NORMAL
   ↑                                                  ↓
   └──────────────────────────────────────────────────┘
```

| State | Duration | What Happens |
|-------|----------|--------------|
| **NORMAL** | Ongoing | Monitor DPS, create checkpoints |
| **MONITOR** | 1 round | Confirm degradation (not noise) |
| **RECOVERY** | 3 rounds | Restore checkpoint, quarantine clients |
| **VALIDATE** | 1 round | Test if recovery worked |
| **RESUME** | Few rounds | Transition back, quarantine expires |

---

## 🐛 The Bug That Was Fixed

### Before (Broken)
```python
if 'recovery' in status_msg.lower():
    self.results['recovery_attempts'] += 1
```
**Result**: Counter always 0 ❌

### After (Fixed)
```python
recovery_attempts_from_fsm = status.get('recovery_attempts', 0)
if recovery_attempts_from_fsm > self.results['recovery_attempts']:
    self.results['recovery_attempts'] = recovery_attempts_from_fsm
```
**Result**: Counter shows actual attempts ✅

---

## 🎨 Design Tokens

### Colors
```css
--neon-cyan: #00f0ff      /* Primary accent */
--neon-green: #00ff9d     /* Success */
--neon-purple: #9d4edd    /* Special */
--neon-red: #ff006e       /* Danger */
```

### Fonts
- **Orbitron**: Headers, metrics
- **Space Grotesk**: Body text
- **JetBrains Mono**: Code, badges

### Effects
- **Glassmorphism**: `backdrop-filter: blur(12px)`
- **Glow**: `box-shadow: 0 0 12px rgba(0, 240, 255, 0.25)`

---

## 📁 Key Files

```
unified_dashboard.py          # Main dashboard (run this!)
run_unified.sh                # Launch script
dashboard/simulator.py        # Simulation engine (bug fixed here)
dashboard/visualizations.py   # Charts
dashboard/explanations.py     # Educational content
```

---

## 🔧 Troubleshooting

### Recovery Counter Shows 0

**Possible Causes:**
1. Self-healing disabled → Enable it
2. No attacks detected → Increase attack intensity
3. DPS below threshold → Lower threshold or stronger attack

**Test Fix:**
- Use "2 Scaling" preset with scale=50
- Should trigger recovery (counter = 1-2)

### UI Looks Plain

**Possible Causes:**
1. Running old dashboard → Use `bash run_unified.sh`
2. CSS not loading → Check Streamlit version ≥1.28
3. Fonts not loading → Check internet connection (Google Fonts)

### Attacks Not Detected

**Possible Causes:**
1. Attack too subtle → Increase scaling factor
2. Threshold too high → Lower to 0.5
3. Not enough rounds → Run 8-10 rounds minimum

---

## ✅ Quick Checklist

**Before Running:**
- [ ] Installed requirements: `pip install -r requirements.txt`
- [ ] System test passed: `python test_setup.py`
- [ ] In correct directory: `/Users/saadansari/CAPS`

**After Running:**
- [ ] Dashboard opened in browser
- [ ] Configured attacks in sidebar
- [ ] Clicked 🚀 EXECUTE
- [ ] Checked recovery counter (should be >0 for attacks)
- [ ] Explored all 4 tabs

**Verification:**
- [ ] Recovery counter shows correct number (not 0)
- [ ] DPS scores match attack configuration
- [ ] FSM timeline shows state transitions
- [ ] Charts display correctly with Cyber HUD theme

---

## 📚 Documentation Index

| Document | Purpose | Read When |
|----------|---------|-----------|
| `README.md` | Quick start | First time |
| `UNIFIED_DASHBOARD.md` | Full guide | Need details |
| `DASHBOARD_COMPARISON.md` | Before/after | Migrating |
| `COMPLETION_SUMMARY.md` | Project summary | Overview |
| `QUICK_REFERENCE.md` | Cheat sheet | **This doc** |

---

## 🎓 Learning Path

1. **Run Demo**: `bash run_unified.sh`
2. **Read Overview Tab**: Understand metrics
3. **Check DPS Tab**: See signal breakdown
4. **Watch Self-Healing Tab**: See FSM in action
5. **Read Explanations Tab**: Learn concepts
6. **Experiment**: Try different attack configs

---

## 💡 Pro Tips

1. **Use "2 Scaling" first** - Most reliable for testing
2. **Check both tabs** - Overview + Self-Healing to verify counter
3. **Lower threshold to 0.5** - Catches subtle attacks
4. **Run 8-10 rounds** - Gives FSM time to react
5. **Watch FSM timeline** - Shows exact state transitions

---

## 🆘 Getting Help

**Check Logs:**
```bash
# Terminal running streamlit shows detailed logs
# Look for lines starting with [SelfHealing]
```

**Common Issues:**
- Recovery counter = 0 → Check attack intensity
- No detection → Lower DPS threshold
- Plain UI → Wrong dashboard (use `bash run_unified.sh`)

**Documentation:**
- Full guide: `UNIFIED_DASHBOARD.md`
- Bug details: `DASHBOARD_COMPARISON.md`
- Project info: `README.md`

---

**Quick Start**: `bash run_unified.sh` 🚀  
**Recommended Config**: "2 Scaling" preset, threshold 0.6  
**Expected Counter**: 1-2 (not 0!)  

*Happy simulating!* 🛡️✨
