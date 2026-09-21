# ASH-FL Dashboard Guide

## 🚀 Quick Start

```bash
bash run_dashboard.sh
```

Dashboard opens at: `http://localhost:8501`

---

## ✨ NEW FEATURES

### 1. Per-Client Attack Assignment

**You can now assign different attacks to different clients!**

#### Quick Presets:
- **2 Scaling**: First 2 clients use scaling attack
- **2 Label-Flip**: First 2 clients use label-flip
- **Mixed Attacks**: Each client gets different attack
- **All Malicious**: All clients are malicious
- **Custom**: Choose attack for each client individually

#### Available Attacks:
- `none` - Honest client
- `scaling` - Scales gradient by large factor (50x)
- `label_flip` - Flips labels during training
- `sign_flip` - Reverses gradient direction
- `backdoor` - Injects backdoor trigger

### 2. Proper Malicious Client Detection Display

**Now shows:**
- ✅ Which clients are malicious (ground truth)
- ✅ Which attack each client is running
- ✅ Whether each malicious client was detected
- ✅ Real-time DPS scores and quarantine status
- ✅ State transitions (NORMAL → MONITOR → RECOVERY)

---

## 📊 How to Use

### Step 1: Configure Simulation

In the **sidebar**:

1. **Simulation Settings**:
   - Number of Clients: 5 (recommended)
   - Number of Rounds: 8 (needs time to detect)
   - Random Seed: 42 (for reproducibility)

2. **Per-Client Attack Setup**:
   - ✅ Enable Attacks
   - Select **Quick Preset** or **Custom**
   
   **Recommended for testing**:
   - Preset: "Mixed Attacks"
   - This gives you: scaling, label_flip, sign_flip attacks simultaneously
   
   **OR Custom**:
   ```
   Client 0: scaling
   Client 1: scaling  
   Client 2: label_flip
   Client 3: none (honest)
   Client 4: none (honest)
   ```
   
   - Scaling Factor: 50.0 (very aggressive)

3. **Self-Healing**:
   - ✅ Enable Self-Healing
   - DPS Threshold: **0.6** (recommended)
   - Recovery Rounds: 3

4. Click **🚀 RUN SIMULATION**

### Step 2: View Results

#### Tab 1: Overview
- **Key Metrics**:
  - Final Accuracy
  - Malicious Clients count
  - **Detection Rate** (how many malicious clients were detected)
  - Recovery Attempts

- **Ground Truth Table**:
  Shows for each client:
  - Status (🔴 Malicious or ✅ Honest)
  - **Attack Type** (what attack they're running)
  - Final DPS score
  - **Detection Status** (✅ Detected or ❌ Missed)

- **Charts**:
  - Accuracy over rounds
  - Loss over rounds

#### Tab 2: DPS Analysis
- **Detailed Scores Table**:
  - G, C, H, P, D individual signals
  - Combined DPS score
  - Trust score
  - Aggregation weight
  - **Action** (Normal, Suspicious, or 🔒 Quarantined)

- **Radar Chart**:
  - Visual breakdown of all 5 signals for any client
  - See which signals trigger for each attack type

#### Tab 3: Self-Healing Monitor
- **Current State**: NORMAL, MONITOR, RECOVERY, etc.
- **State Timeline**: See when transitions happened
- **Quarantine Heatmap**: Which clients were quarantined when
- **Event Log**: Detailed log of all detection/recovery events

#### Tab 4: Explanations
- Educational content about DPS, self-healing, etc.

---

## 🎯 Expected Behavior

### With Mixed Attacks (Recommended Test)

```
Client 0: scaling      → High G, High H → DPS ~0.6-0.7 ✅ Detected
Client 1: scaling      → High G, High H → DPS ~0.6-0.7 ✅ Detected  
Client 2: label_flip   → Low G, High P  → DPS ~0.4-0.5 ⚠️  Borderline
Client 3: none (honest)→ All low        → DPS ~0.3     ✅ Correct
Client 4: none (honest)→ All low        → DPS ~0.3     ✅ Correct
```

### Self-Healing Timeline

```
Rounds 1-4: NORMAL (building history, DPS increasing)
Round 5-6:  MONITOR (DPS > 0.6 detected, watching)
Round 6-7:  RECOVERY (persistent attack confirmed, quarantine + restore)
Round 8+:   VALIDATE/RESUME (checking if recovery worked)
```

### Quarantine Effects

**Before quarantine**:
- Malicious client weight: ~0.33 (equal to others)

**After quarantine**:
- Malicious client weight: ~0.05-0.1 (reduced 90%)
- Honest client weights increase proportionally

---

## 🔍 Attack Detection Rates

| Attack Type | Typical DPS | Detection Rate |
|-------------|-------------|----------------|
| **Scaling (50x)** | 0.6-0.7 | ✅ 95-100% |
| **Sign Flip** | 0.5-0.6 | ✅ 80-90% |
| **Label Flip** | 0.4-0.5 | ⚠️  50-70% |
| **Backdoor** | 0.4-0.6 | ⚠️  60-80% |

**Why scaling is best detected**:
- Creates huge gradient deviations (G ≈ 1.0)
- Causes sudden behavior change (H ≈ 0.8-1.0)
- Easy to spot with normalized MAD

**Why label-flip is harder**:
- Updates look normal magnitude (G ≈ 0.3-0.4)
- Only P signal catches it (via accuracy drop)
- Requires more rounds to accumulate confidence

---

## 💡 Tips for Best Results

### For Reliable Detection:
1. **Use scaling attack** with factor 50+ for at least one client
2. **Run 8+ rounds** (needs time to build history)
3. **Keep threshold at 0.6** (balanced sensitivity)
4. **Use 5 clients** (3 honest, 2 malicious is good ratio)

### For Testing Edge Cases:
1. **All malicious**: Set all clients to attacks
   - System should detect majority as suspicious
   - Recovery may struggle (not enough honest clients)

2. **Single malicious**: Only 1 attacker
   - Should quarantine quickly
   - Clean recovery expected

3. **Mixed attacks**: Different attack per client
   - Most realistic scenario
   - Shows which attacks are detected better

### For Performance:
1. **Fewer rounds** = faster simulation
2. **Fewer clients** = faster per round
3. **Disable self-healing** for pure detection testing

---

## 🐛 Troubleshooting

### "Self-healing not triggering"

**Check**:
1. DPS threshold = 0.6 (not 2.0!)
2. Attack type = scaling (not label_flip)
3. Number of rounds ≥ 6 (needs history)
4. Malicious clients ≥ 1

**If still not working**:
- Check terminal output for DPS scores
- Should see: `[Round X] Max DPS: 0.XXX`
- If max DPS < 0.6, try:
  - Increase scaling factor to 100
  - Use more malicious clients

### "No malicious clients shown"

**Check**:
1. ✅ Enable Attacks is checked
2. At least one client has attack != "none"
3. Look at "Ground Truth & Attack Assignment" table in Overview tab

### "Detection rate is 0%"

**Check**:
1. DPS threshold too high (should be 0.6)
2. Attack too subtle (use scaling not label_flip)
3. Not enough rounds (try 8-10)

---

## 📈 Understanding the Metrics

### DPS Score Breakdown

```
DPS = 0.33×G + 0.28×C + 0.22×H + 0.17×P + 0.00×D
```

**For scaling attack (50x)**:
- G ≈ 1.0 (maxed out - huge deviation)
- C ≈ 0.0-0.2 (similar direction but large)
- H ≈ 0.8-1.0 (behavior changed suddenly)
- P ≈ 0.3-1.0 (hurts accuracy)
- **DPS ≈ 0.6-0.7** ✅ Above threshold!

**For honest client**:
- G ≈ 0.2-0.3 (normal variation)
- C ≈ 0.0-0.1 (aligned with consensus)
- H ≈ 0.1-0.2 (consistent behavior)
- P ≈ 0.0-0.1 (helps accuracy)
- **DPS ≈ 0.2-0.3** ✅ Below threshold!

### State Machine

```
┌────────┐
│ NORMAL │ ← Healthy operation
└───┬────┘
    │ DPS > 0.6 detected
    ▼
┌─────────┐
│ MONITOR │ ← Watching for persistence
└───┬─────┘
    │ Attack persists
    ▼
┌──────────┐
│ RECOVERY │ ← Quarantine + checkpoint restore
└───┬──────┘
    │ Recovery complete
    ▼
┌──────────┐
│ VALIDATE │ ← Test recovery success
└───┬──────┘
    │ Success or failure
    ▼
┌────────┐
│ RESUME │ ← Back to normal or retry
└────────┘
```

---

## 🎓 Learning Exercises

### Exercise 1: Single Attack Type
Run with all clients using same attack (all scaling).
- **Question**: Do all malicious clients get same DPS?
- **Answer**: No! Random variation in data causes different G/H scores.

### Exercise 2: Mixed Attacks
Run with different attack per client.
- **Question**: Which attack has highest DPS?
- **Answer**: Usually scaling, then sign_flip, then label_flip.

### Exercise 3: Threshold Tuning
Run same config with different thresholds (0.4, 0.6, 0.8).
- **Question**: How does detection rate change?
- **Answer**: Lower threshold = more detections but more false positives.

### Exercise 4: Attack Strength
Try scaling factors: 10, 50, 100.
- **Question**: How does DPS change?
- **Answer**: Higher factor → higher G → higher DPS (but diminishing returns due to normalization).

---

## 🎉 You're Ready!

The dashboard now properly displays:
- ✅ Malicious client detection with % accuracy
- ✅ Per-client attack type assignment  
- ✅ Real-time DPS scores and quarantine status
- ✅ Self-healing state machine transitions
- ✅ Detailed signal breakdowns

**Start experimenting with different attack combinations!**
