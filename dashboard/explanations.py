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

Different attacks can produce different signals, though detection is not guaranteed:
- **Label-flip attacks** → High P (bad performance) + moderate loss spike
- **Sign-flip attacks** → High C (wrong direction)
- **Scaling attacks** → High G (large magnitude)
- **Backdoor attacks** → High H (inconsistent behavior) + High P

These signals can help distinguish attack behavior, but no signal or threshold guarantees detection.

### Formula (Updated)

$$DPS_i = w_G \\cdot G_i + w_C \\cdot C_i + w_H \\cdot H_i + w_P \\cdot P_i + w_D \\cdot D_i$$

**Current weights** (D weight redistributed, P increased for label-flip detection):
- $w_G = 0.27$ 
- $w_C = 0.27$ 
- $w_H = 0.19$ 
- $w_P = 0.27$ (significantly increased for better label-flip detection)
- $w_D = 0.00$ - **DISABLED for privacy**

### Normalization

All signals normalized to [0, 1] using adaptive functions before weighting:
- **G**: Sigmoid of the median MAD-normalized delta deviation, centered at 2.0
- **C**: `clip(1 - cosine_similarity, 0, 1)`
- **H**: `tanh(raw_history_deviation / 2)`
- **P**: Sigmoid of the shadow-validation impact score, centered at 0.5
- **D**: Always 0.0 (disabled)

The configured threshold defaults to **0.55** and can be changed in the simulator. A score above the threshold contributes to suspicious-client and recovery decisions; it does not prove a client is malicious.
"""
    
    explanations["📊 G - Gradient Deviation"] = """
**G measures how far a client's update is from the typical update.**

### Calculation

1. Compute each client's local model delta from the current global model
2. Compute the **median delta** across participating clients (robust to outliers)
3. Compute **MAD** (Median Absolute Deviation) as a robust scale estimate
4. Divide each client's coordinate deviation from the median by MAD and take the median deviation

### Interpretation

The dashboard displays G after sigmoid normalization to [0, 1]. The raw score is a median coordinate deviation divided by MAD; it is not a probability.

### Why Median + MAD?

Unlike mean and standard deviation, median and MAD are less sensitive to outliers. They do not guarantee a correct consensus if most participating clients are malicious.

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

The resulting raw score is capped and mapped through a sigmoid centered at 2.0.
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
   - Accuracy degradation: `acc_score = max(0, (baseline_acc - updated_acc) / 0.05)`
   - Relative loss increase: `loss_score = max(0, ((updated_loss - baseline_loss) / baseline_loss) / 0.3)`
6. Take the **maximum** of both: `P = max(acc_score, loss_score)`
7. Map P through a sigmoid centered at 0.5 to get the displayed normalized P signal.

### Why Both Accuracy and Loss?

**Label-flip attacks** often show:
- A decrease in validation accuracy
- An increase in validation loss

By checking both, we catch label-flip more reliably even when accuracy degradation is subtle.

### Interpretation

- **P raw = 0**: No measured degradation
- **P raw = 1.0**: 5% accuracy drop OR 30% relative loss increase
- Displayed P is sigmoid-normalized raw P, not a probability.

### Sensitivity

The implementation uses 0.05 as the accuracy-drop scale and 0.3 as the relative-loss scale. These are design thresholds, not guarantees of detection.

### Why Performance?

This signal measures the impact of an update on the held-out validation data; poor impact does not by itself establish that an update is malicious.

### Computational Cost

This signal requires extra model evaluation.
- Only computed for participating clients each round
- Uses the configured validation subset of held-out data
- Separate from final evaluation set

### Validation Set

Critical requirements:
- **Clean** - no poisoned samples
- **Representative** - matches global distribution
- **Held-out** - never used for training
- Size depends on the dataset and the desired uncertainty; no fixed count is assumed sufficient.

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

P is computed by evaluating a copied model on held-out validation records; it does not identify an attack with certainty.
"""
    
    explanations["📦 D - Data Quality"] = """
**D assesses the quality of a client's local dataset.**

### ⚠️ CURRENT STATUS: DISABLED (D = 0.0 for all clients)

**Why is D disabled?**  
This implementation does not compute or report a data-quality score. A deployment could compute such a signal on each client and share an explicitly defined summary. The detector does not inspect individual client training records, and this project does not fabricate a proxy.

**What would D measure (if we could access local data)?**
- **Class balance**: Is one class over-represented?
- **Feature variance**: Are features informative?
- **Sample count**: Does client have enough data?
- **Label noise**: Are labels consistent?
- **Outlier detection**: Are there corrupted samples?

**D stays at 0 because it is disabled.** The dashboard reports four computed signals and marks D unavailable by design.
"""
    
    explanations["🤝 Trust & Reputation"] = """
**Trust scores track long-term client reliability.**

### Update Rule

$$R_i^{(t+1)} = R_i^{(t)} \\cdot (1 - \\alpha \\cdot DPS_i^{(t)})$$

- **Low DPS**: Trust decays more slowly
- **High DPS**: Trust decays
- **Minimum**: $R_i \\geq 0.01$ (always allow small weight)

Default: $\\alpha = 0.1$ (decay rate)

### Why Trust?

**Aggregation uses a running trust value.** A high DPS reduces that value; the current update rule does not increase trust after a clean round.

### Aggregation Weight

$$a_i = n_i \\cdot R_i^2 \\cdot (1 - \\min(DPS_i/10, 0.99))^{1.5}$$

Where:
- $n_i$: Number of samples
- $R_i$: Trust score
- Trust sensitivity exponent: 2.0
- DPS penalty exponent: 1.5
- Quarantine applies an additional configured multiplier.

### Effect

- **Honest clients**: High trust → high weight
- **Malicious clients**: Low trust → near-zero weight
- **Reformed clients**: This implementation does not restore trust automatically
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
