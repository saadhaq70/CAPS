# Network Topology Visualization - New Feature

## Overview

Added **dynamic network topology visualization** to the Overview tab showing the federated learning network as a visual graph with central server and client nodes.

## Location

**Tab**: 📊 OVERVIEW  
**Position**: Left side (replaces one of the charts)

## Visual Elements

### Central Server 🔷
- **Shape**: Blue hexagon
- **Size**: Large (55px)
- **Color**: Neon cyan (#00f0ff)
- **Position**: Center of graph
- **Label**: "SERVER"
- **Tooltip**: "FedAvg Aggregator - Coordinates FL training"

### Client Nodes 
Arranged in a circle around the server:

#### Active Honest Clients 🟢
- **Shape**: Circle
- **Size**: Medium (36px)
- **Color**: Neon green (#00ff9d)
- **Lines**: Cyan, solid, medium thickness
- **Label**: "C0", "C1", etc.
- **Tooltip**: "Client X - ACTIVE (DPS: 0.xxx)"

#### Standby Clients ⚫
- **Shape**: Circle
- **Size**: Small (28px)
- **Color**: Gray (#475569)
- **Lines**: Gray, dotted, thin
- **Label**: "C0", "C1", etc.
- **Tooltip**: "Client X - STANDBY"

#### Malicious Clients ❌
- **Shape**: X mark
- **Size**: Medium-Large (32-40px depending on active)
- **Color**: Red (#ff006e) with **DPS-based intensity**
  - Low DPS (0.0-0.3): Lighter red (50% opacity)
  - Medium DPS (0.3-0.6): Medium red (65% opacity)
  - High DPS (0.6-1.0): Bright red (80-100% opacity)
- **Lines**: Red with DPS-based intensity, solid if active
- **Label**: "C0", "C1", etc.
- **Tooltip**: "Client X - MALICIOUS (DPS: 0.xxx)"

### Connection Lines
- **Active honest**: Cyan, solid, medium thickness
- **Active malicious**: Red (intensity = DPS), solid, thick
- **Standby**: Gray, dotted, thin

## Features

### 1. Real-Time DPS Integration
- Malicious client color intensity reflects DPS score
- Higher DPS = brighter/more intense red
- Helps visually identify which malicious clients are being detected

### 2. Active/Standby Status
- Shows which clients participated in the final round
- Active clients have solid lines and larger markers
- Standby clients are grayed out with dotted lines

### 3. Attack Type Identification
- Malicious clients marked with X symbols
- Honest clients use circles
- Easy to distinguish at a glance

### 4. Interactive Tooltips
- Hover over any node to see details:
  - Client ID
  - Status (ACTIVE/STANDBY/MALICIOUS)
  - Current DPS score

## Code Structure

### Function Location
`unified_dashboard.py` (lines ~20-140)

```python
def create_topology_figure(num_nodes, active_nodes, malicious_nodes, results):
    """
    Create network topology visualization.
    
    Args:
        num_nodes: Total number of clients
        active_nodes: List of active client IDs (participated in this round)
        malicious_nodes: List of malicious client IDs (ground truth)
        results: Simulation results (contains DPS scores)
    
    Returns:
        Plotly figure
    """
    # 1. Draw connection lines (server → clients)
    # 2. Draw client nodes (with DPS-based coloring)
    # 3. Draw central server node
    # 4. Style and layout
```

### Integration
Called from `render_overview_tab()`:

```python
def render_overview_tab(results, dps_threshold, num_clients):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Network topology (NEW!)
        malicious_clients = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
        selected_clients = results['rounds'][-1].get('selected_clients', [])
        
        fig_topo = create_topology_figure(num_clients, selected_clients, malicious_clients, results)
        st.plotly_chart(fig_topo, use_container_width=True)
    
    with col2:
        # Accuracy chart (moved here)
        fig_acc = create_accuracy_chart(results)
        st.plotly_chart(fig_acc, use_container_width=True)
```

## Design Alignment

### Cyber HUD Theme
- ✅ Uses neon colors (cyan, green, red)
- ✅ Glassmorphism background: `rgba(13, 17, 27, 0.75)`
- ✅ Orbitron font for labels
- ✅ Glowing effects on active connections
- ✅ Dark background with transparency

### Consistency
- Colors match the badge system:
  - Cyan = primary/server
  - Green = honest/success
  - Red = malicious/danger
  - Gray = inactive/neutral

## Usage Example

### Scenario: 5 clients, 2 malicious (scaling attack)

**Before simulation:**
```
All nodes gray (standby)
No connections visible
Server in center
```

**After simulation (Round 8):**
```
Server (center): Blue hexagon
├─ Client 0: Red X (DPS: 0.52, bright red)  ← Malicious, detected
├─ Client 1: Red X (DPS: 0.27, medium red) ← Malicious, partially detected
├─ Client 2: Green circle (DPS: 0.13)      ← Honest, active
├─ Client 3: Green circle (DPS: 0.29)      ← Honest, active
└─ Client 4: Gray circle (standby)         ← Not selected this round
```

## Benefits

### 1. Visual Understanding
- Quickly see network structure
- Identify malicious clients at a glance
- Understand which clients are active

### 2. Detection Validation
- Red intensity shows DPS → easy to verify detection
- Compare visual with DPS table below
- Immediate feedback on attack severity

### 3. Educational Value
- Shows FL architecture clearly
- Server-client relationship visible
- Active aggregation process illustrated

### 4. Professional Presentation
- Matches Cyber HUD aesthetic
- Suitable for demos and presentations
- Engaging visual element

## Comparison with Original app.py

| Feature | app.py | unified_dashboard.py |
|---------|--------|---------------------|
| **Topology Graph** | ✅ Yes | ✅ Yes (added) |
| **Real DPS Colors** | ❌ No (random) | ✅ Yes (from simulation) |
| **Malicious Marking** | ❌ No | ✅ Yes (X symbols) |
| **DPS Intensity** | ❌ No | ✅ Yes (color opacity) |
| **Active/Standby** | ✅ Yes | ✅ Yes |
| **Tooltips** | ✅ Basic | ✅ Detailed (with DPS) |
| **Real Simulation** | ❌ No | ✅ Yes |

## Future Enhancements

Possible improvements for later:

1. **Animation**: Show round-by-round changes
2. **Click interaction**: Click node to see detailed DPS breakdown
3. **Edge labels**: Show aggregation weights on connections
4. **Quarantine visual**: Different styling for quarantined clients
5. **FSM state indicator**: Color-code server by FSM state

## Testing

### Verify It Works

1. Run unified dashboard:
   ```bash
   bash run_unified.sh
   ```

2. Configure simulation with attacks

3. Click EXECUTE

4. Go to 📊 OVERVIEW tab

5. **Check topology graph** (left side):
   - ✅ Central server visible (blue hexagon)
   - ✅ Client nodes arranged in circle
   - ✅ Malicious clients marked with red X
   - ✅ Active clients highlighted
   - ✅ Hover shows tooltips

### Expected Appearance

```
        C2 (green)
           /
          /
    C1 (red X) ---- 🔷 SERVER ---- C3 (green)
          \            |
           \           |
        C0 (red X)   C4 (gray)
```

## Summary

✅ **Added**: Dynamic network topology visualization  
✅ **Location**: Overview tab, left column  
✅ **Features**: Real DPS coloring, malicious marking, active/standby status  
✅ **Design**: Matches Cyber HUD theme perfectly  
✅ **Benefit**: Visual understanding of FL network and attack detection  

The unified dashboard now has **all features** from both original dashboards:
- Beautiful Cyber HUD design ✅
- Real DPS and self-healing ✅
- Network topology visualization ✅ (NEW)
- Fixed recovery counter ✅
