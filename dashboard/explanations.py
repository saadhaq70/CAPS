"""
Explanation content for the dashboard.
Provides educational content about ASH-FL concepts.
"""

def get_explanation_content() -> dict:
    """
    Return dictionary of explanation sections.
    
    Returns:
        Dictionary mapping section titles to markdown content
    """
    explanations = {}
    
    explanations["🔍 What is DPS?"] = """
**Dynamic Poisoning Score (DPS)** is a composite metric that quantifies how suspicious a client's behavior is during federated learning.

Unlike simple distance metrics, DPS combines **multiple independent signals** to catch different attack patterns:

- **G (Gradient Deviation)**: How far is this update from the median?
- **C (Cosine Disagreement)**: Is the update pointing in the wrong direction?
- **H (History Deviation)**: Has this client's behavior suddenly changed?
- **P (Performance Impact)**: Does this update hurt model accuracy? ✅ REAL
- **D (Data Quality)**: ⚠️ DISABLED (requires local data access - violates FL privacy)

### Why Multiple Signals?

Different attacks have different signatures:
- **Label-flip attacks** → High P (bad performance) + moderate loss spike
- **Sign-flip attacks** → High C (wrong direction)
- **Scaling attacks** → High G (large magnitude)
- **Backdoor attacks** → High H (inconsistent behavior) + High P

By combining signals, DPS catches them all!

### Formula (Updated)

$$DPS_i = w_G \\cdot G_i + w_C \\cdot C_i + w_H \\cdot H_i + w_P \\cdot P_i + w_D \\cdot D_i$$

**Current weights** (D weight redistributed, P increased for label-flip detection):
- $w_G = 0.30$ 
- $w_C = 0.27$ 
- $w_H = 0.20$ 
- $w_P = 0.23$ (increased from 0.17 to better catch subtle attacks)
- $w_D = 0.00$ - **DISABLED for privacy**

### Normalization

All signals normalized to [0, 1] using adaptive functions before weighting:
- **G**: Sigmoid centered at 2.0 (suspicious if > 2σ from median)
- **C**: Linear clipping to [0, 1] (suspicious if cosine similarity < 0)
- **H**: Tanh for smooth saturation (suspicious if > 2σ from history)
- **P**: Sigmoid centered at 0.5 (suspicious if accuracy drops > 5% or loss spikes)
- **D**: Always 0.0 (disabled)

**Typical threshold**: DPS > 0.6-0.7 flags client as suspicious (normalized scale)
"""
    
    explanations["📊 G - Gradient Deviation"] = """
**G measures how far a client's update is from the typical update.**

### Calculation

1. Compute **median update** across all clients (robust to outliers)
2. Compute **MAD** (Median Absolute Deviation) as a robust scale estimate
3. For each client: $G_i = \\frac{|\\Delta_i - \\text{median}|}{\\text{MAD}}$

### Interpretation

- **G < 2**: Normal variation
- **G > 2**: Potential outlier (3σ rule analog)
- **G > 5**: Very suspicious

### Why Median + MAD?

Unlike mean and standard deviation, median and MAD are **robust to outliers**. Even if 40% of clients are malicious, the median still represents honest behavior.

### What Attacks Trigger High G?

- ✅ **Scaling attacks** (amplified gradients)
- ✅ **Random noise attacks**
- ❌ Sign-flip (same magnitude, different direction)
"""
    
    explanations["🧭 C - Cosine Disagreement"] = """
**C measures the angular distance between a client's update and the consensus direction.**

### Calculation

1. Compute **median update** direction
2. For each client: $\\text{cosine\\_sim} = \\frac{\\Delta_i \\cdot \\text{median}}{||\\Delta_i|| \\cdot ||\\text{median}||}$
3. Convert to disagreement: $C_i = 1 - \\text{cosine\\_sim}$

### Interpretation

- **C = 0**: Perfect alignment (same direction)
- **C = 1**: Orthogonal (90° angle)
- **C = 2**: Opposite direction (180° angle)

### Why Cosine?

Cosine similarity is **magnitude-independent**. A small step in the wrong direction is just as bad as a large one.

### What Attacks Trigger High C?

- ✅ **Sign-flip attacks** (reversed gradients)
- ✅ **Backdoor attacks** (different objective)
- ❌ Scaling (same direction, different magnitude)
"""
    
    explanations["📈 H - History Deviation"] = """
**H compares a client's current behavior to its historical profile.**

### Calculation

1. Maintain **EMA (Exponential Moving Average)** of past updates for each client
2. Compute standard deviation of historical updates
3. For each client: $H_i = \\frac{|\\Delta_i - EMA_i|}{\\sigma_i}$

### Interpretation

- **H < 2**: Consistent with past behavior
- **H > 3**: Sudden change (potential attack start)
- **First rounds**: H = 0 (no history yet)

### Why History?

Some attacks are **adaptive**: malicious clients behave normally early to build trust, then attack later. History deviation catches this shift.

### What Attacks Trigger High H?

- ✅ **Time-delayed attacks**
- ✅ **Intermittent poisoning**
- ❌ Persistent attacks (H adapts over time)

### EMA Update

$$EMA_{t} = \\alpha \\cdot \\Delta_t + (1-\\alpha) \\cdot EMA_{t-1}$$

Default: $\\alpha = 0.3$ (balances responsiveness vs stability)
"""
    
    explanations["🎯 P - Performance Impact"] = """
**P estimates how much a client's update would hurt global model performance.**

### ✅ REAL IMPLEMENTATION (Enhanced Shadow Validation)

**How it works:**
1. Create **shadow model** with current global parameters
2. Get baseline accuracy **and loss** on clean validation set
3. Apply the client's update to shadow model
4. Measure new accuracy and loss on same validation set
5. Compute **both** degradation signals:
   - Accuracy degradation: `acc_score = (baseline_acc - updated_acc) / 0.08`
   - Loss spike: `loss_score = (updated_loss - baseline_loss) / baseline_loss / 0.5`
6. Take the **maximum** of both: `P = max(acc_score, loss_score)`

### Why Both Accuracy and Loss?

**Label-flip attacks** often show:
- Moderate accuracy drop (5-8%)
- Large loss spike (30-50% increase)

By checking both, we catch label-flip more reliably even when accuracy degradation is subtle.

### Interpretation

- **P = 0**: No degradation (helpful update)
- **P = 0.5**: Moderate degradation (suspicious)
- **P = 1.0**: 8% accuracy drop OR 50% loss increase (very harmful)
- **P > 1.0**: Severe degradation (strong attack signal)

### Sensitivity

More sensitive than before (0.08 vs 0.10 accuracy threshold):
- Catches subtle poisoning earlier
- May increase false positives slightly (acceptable trade-off)
- Loss check provides secondary validation

### Why Performance?

This is the **ultimate ground truth**: if an update hurts accuracy or spikes loss, it's poisoned by definition.

### Computational Cost

**Most expensive signal** - requires model evaluation.
- Only computed for participating clients each round
- Uses held-out validation set (50% of test data)
- Separate from final evaluation set
- ~10-20ms per client (acceptable overhead)

### Validation Set

Critical requirements:
- **Clean** - no poisoned samples
- **Representative** - matches global distribution
- **Held-out** - never used for training
- **Small** - 30-50 samples sufficient for binary classification

### What Attacks Trigger High P?

- ✅ **Label-flip attacks** (forces wrong predictions + loss spike)
- ✅ **Sign-flip attacks** (moves away from optimal)
- ✅ **Backdoor attacks** (degrades main task performance)
- ✅ **All attacks** (eventually degrade performance)
- ✅ **Subtle poisoning** (even if G, C, H are low)

### Fallback Behavior

If validation data unavailable:
- Falls back to distance-based proxy: `P ≈ ||update|| / 10`
- Clearly marked in logs
- Less accurate but prevents crashes

**Bottom line**: P is now REAL shadow validation with dual accuracy+loss checks for better label-flip detection.
"""
    
    explanations["📦 D - Data Quality"] = """
**D assesses the quality of a client's local dataset.**

### ⚠️ CURRENT STATUS: DISABLED (D = 0.0 for all clients)

**Why is D disabled?**  
Computing real data quality requires analyzing the client's local dataset distribution (class balance, feature variance, label noise, etc.). This **violates Federated Learning privacy principles** - the core tenet of FL is that the server should never access raw client data.

**What would D measure (if we could access local data)?**
- **Class balance**: Is one class over-represented?
- **Feature variance**: Are features informative?
- **Sample count**: Does client have enough data?
- **Label noise**: Are labels consistent?
- **Outlier detection**: Are there corrupted samples?

### Weight Redistribution

Since D cannot be computed honestly, its weight has been redistributed to strengthen the other signals:

**Updated weights** (effective now):
- $w_G = 0.30$ (was 0.28)
- $w_C = 0.27$ (was 0.25)
- $w_H = 0.20$ (unchanged)
- $w_P = 0.23$ (was 0.15) - **significantly increased for label-flip detection**
- $w_D = 0.00$ (was 0.10) - **DISABLED**

### Privacy vs. Detection Trade-off

This is a fundamental constraint in Federated Learning:
- ✅ **Privacy preserved**: Server never sees raw client data
- ✅ **Honest system**: We don't pretend to compute D
- ❌ **Reduced detection**: One less signal available

However, the other four signals (G, C, H, P) are sufficient to catch most attacks:
- **G** catches magnitude-based attacks (scaling)
- **C** catches direction-based attacks (sign-flip)
- **H** catches temporal attacks (delayed poisoning)
- **P** catches performance-degrading attacks (label-flip, backdoor)

### Future Approximations

Could potentially approximate D from **indirect signals** without data access:
- High update variance → possibly noisy local data
- Consistent convergence → likely good quality
- Update stability → stable dataset

But these are weak proxies and may not be worth the complexity.

### Bottom Line

**Honest FL means we can't peek at local data, so D stays at 0.**  
The P signal (performance impact via shadow validation) now carries more weight to compensate, especially for catching subtle attacks like label-flip.
"""
    
    explanations["🤝 Trust & Reputation"] = """
**Trust scores track long-term client reliability.**

### Update Rule

$$R_i^{(t+1)} = R_i^{(t)} \\cdot (1 - \\alpha \\cdot DPS_i^{(t)})$$

- **Low DPS**: Trust grows (or stays high)
- **High DPS**: Trust decays
- **Minimum**: $R_i \\geq 0.01$ (always allow small weight)

Default: $\\alpha = 0.1$ (decay rate)

### Why Trust?

**Aggregation should favor reliable clients.** One bad round shouldn't destroy a client's reputation, but repeated misbehavior should.

### Aggregation Weight

$$a_i = n_i \\cdot R_i^\\gamma \\cdot (1 - DPS_i)^\\eta$$

Where:
- $n_i$: Number of samples
- $R_i$: Trust score
- $\\gamma$: Trust sensitivity (default: 2.0)
- $\\eta$: DPS penalty (default: 1.5)

### Effect

- **Honest clients**: High trust → high weight
- **Malicious clients**: Low trust → near-zero weight
- **Reformed clients**: Trust can recover if they behave
"""
    
    explanations["🛡️ Self-Healing FSM"] = """
**Self-healing uses a Finite State Machine to coordinate recovery.**

### States

1. **NORMAL**: Healthy operation, monitoring metrics
2. **MONITOR**: Degradation detected, confirming it's not noise
3. **RECOVERY**: Checkpoint restored, retraining with quarantine
4. **VALIDATE**: Testing if recovery worked
5. **RESUME**: Recovery successful, returning to normal

### Transitions

```
NORMAL → MONITOR: Health metrics degrade
MONITOR → RECOVERY: Degradation confirmed
RECOVERY → VALIDATE: Retraining complete
VALIDATE → RESUME: Validation passed
VALIDATE → RECOVERY: Validation failed (expand quarantine)
RESUME → NORMAL: Quarantine expired
```

### Health Metrics

System monitors:
- **Accuracy drop** > 15%
- **Loss spike** > 30%
- **Avg DPS** > threshold
- **Suspicious fraction** > 30%
- **Model drift** (L2 distance)

### Recovery Algorithm

1. **Freeze** candidate model
2. **Identify** top suspicious clients (by DPS)
3. **Restore** last trusted checkpoint
4. **Quarantine** suspicious clients (down-weight to 0.1×)
5. **Retrain** for N rounds (default: 3)
6. **Validate** recovered model
7. **Accept** if improved, else retry with expanded quarantine

### Quarantine

- Clients are not excluded, just **down-weighted**
- Temporary (expires after 5 rounds)
- Prevents starvation
- Allows recovery from false positives
"""
    
    explanations["⚙️ Configuration & Tuning"] = """
### Key Hyperparameters

#### DPS Calculation
- **Signal weights**: $w_G, w_C, w_H, w_P, w_D$ (default: 0.30, 0.25, 0.20, 0.15, 0.10)
- **DPS threshold**: 2.0 (lower = more sensitive)

#### Trust System
- **Trust decay**: $\\alpha = 0.1$ (how fast trust drops)
- **Trust sensitivity**: $\\gamma = 2.0$ (how much trust affects aggregation)
- **DPS penalty**: $\\eta = 1.5$ (how much DPS affects aggregation)

#### Self-Healing
- **Accuracy drop threshold**: 0.15 (15%)
- **Loss spike threshold**: 0.30 (30%)
- **Recovery rounds**: 3
- **Quarantine window**: 5 rounds
- **Suspicious weight**: 0.1 (down-weighting factor)
- **Max recovery attempts**: 3

### Tuning Guidelines

**More sensitive detection:**
- Lower DPS threshold (1.5)
- Increase signal weights for G, C
- Lower accuracy drop threshold (0.10)

**More robust to false positives:**
- Higher DPS threshold (2.5)
- Increase baseline window (5 rounds)
- Lower trust decay (0.05)

**Faster recovery:**
- Reduce recovery rounds (2)
- Increase suspicious weight (0.2)
- Reduce quarantine window (3)

### Attack-Specific Tips

- **Label-flip**: Increase $w_P$, lower accuracy threshold
- **Sign-flip**: Increase $w_C$, lower DPS threshold
- **Scaling**: Increase $w_G$, use higher DPS threshold
- **Backdoor**: Increase $w_H$, longer baseline window
"""
    
    explanations["🎓 How to Use This Dashboard"] = """
### Getting Started

1. **Configure** your simulation in the sidebar:
   - Choose number of clients and rounds
   - Enable attacks (or run clean baseline)
   - Enable self-healing to see recovery

2. **Run** the simulation:
   - "Full Run": See complete results immediately
   - "Step-by-Step": Walk through each round

3. **Explore** the tabs:
   - **Overview**: Quick summary and key metrics
   - **Attack & Performance**: Detailed accuracy/loss charts
   - **DPS Deep Dive**: Most important! See signal breakdowns
   - **Trust & Aggregation**: How weights evolve
   - **Self-Healing Monitor**: Recovery timeline
   - **Explanations**: This section

### Understanding Results

#### In the DPS Deep Dive Tab:

- **Red rows** = Malicious clients (ground truth)
- **Green rows** = Honest clients
- **DPS > threshold** = Flagged as suspicious
- **Radar chart** = Visual breakdown of G, C, H, P, D

#### What to Look For:

✅ **Good detection**: Malicious clients have high DPS  
✅ **Low false positives**: Honest clients have low DPS  
✅ **Recovery**: Accuracy improves after attack  
❌ **Missed attack**: Malicious client has low DPS  
❌ **False positive**: Honest client quarantined

### Experiments to Try

1. **Baseline**: Run with no attacks → all DPS should be low
2. **Single attack**: Enable one attack type → see which signals fire
3. **Multiple attackers**: Increase malicious clients → test robustness
4. **No self-healing**: Disable recovery → see accuracy degrade
5. **Step-by-step**: Watch exactly when system detects and recovers

### Reading the Radar Chart

- **Malicious clients**: Usually 2-3 signals are high
- **Honest clients**: All signals stay low
- **Attack type matters**: Sign-flip = high C, Scaling = high G
"""
    
    return explanations
