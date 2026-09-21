"""
⚠️ DEPRECATED: This dashboard is deprecated and for visual reference only.

Please use the unified dashboard instead:
    bash run_unified.sh

The unified dashboard has:
- All the visual design from this file
- Real DPS computation and self-healing functionality
- Fixed bugs and complete features

---

CAPS // ASH-FL Federated Learning Command Console
UI Design: Cyber HUD inspired by khaledoghli.com (Orbitron, Space Grotesk, Neon Glassmorphism)
"""

import os
import sys
import time
import yaml
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure project root is available for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from clients.data_loader import HeartDiseaseDataLoader
    from clients.client import HeartDiseaseNet
    MODULES_AVAILABLE = True
except Exception:
    MODULES_AVAILABLE = False

# ==============================================================================
# Page Configuration
# ==============================================================================
st.set_page_config(
    page_title="CAPS // FL Command Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ⚠️ VISUAL DEMO MODE WARNING
# ==============================================================================
st.markdown("""
<div style="
    background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
    border: 3px solid #ff6b35;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 20px 0 30px 0;
    box-shadow: 0 8px 32px rgba(255, 107, 53, 0.4);
    animation: pulse-warning 2s ease-in-out infinite;
">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div style="font-size: 3rem;">⚠️</div>
        <div>
            <h2 style="margin: 0 0 8px 0; color: #ffffff; font-size: 1.5rem; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                VISUAL DEMO MODE
            </h2>
            <p style="margin: 0; color: #ffffff; font-size: 1.05rem; line-height: 1.5;">
                <strong>This interface displays illustrative animations and placeholder metrics only.</strong><br/>
                For <strong>real detection, DPS computation, and self-healing</strong>, please use:<br/>
                👉 <code style="background: rgba(255,255,255,0.2); padding: 4px 8px; border-radius: 4px; font-weight: bold;">dashboard_app.py</code> 
                (run: <code style="background: rgba(255,255,255,0.2); padding: 4px 8px; border-radius: 4px;">bash run_dashboard.sh</code>)
            </p>
        </div>
    </div>
</div>

<style>
@keyframes pulse-warning {
    0%, 100% { box-shadow: 0 8px 32px rgba(255, 107, 53, 0.4); }
    50% { box-shadow: 0 8px 48px rgba(255, 107, 53, 0.7); }
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# Cyber HUD Stylesheet (khaledoghli.com inspired)
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Space+Grotesk:wght@300;400;500;600&family=JetBrains+Mono:wght@300;400;500;700&display=swap');

:root {
    --bg-dark: #07090e;
    --card-bg: rgba(13, 17, 27, 0.78);
    --border-glow: rgba(0, 240, 255, 0.22);
    --neon-cyan: #00f0ff;
    --neon-green: #00ff9d;
    --neon-purple: #9d4edd;
    --text-primary: #f1f5f9;
    --text-muted: #64748b;
}

/* Background & Core Layout */
.stApp {
    background: radial-gradient(circle at 50% 0%, #0d1527 0%, #06080d 65%, #030407 100%) !important;
    font-family: 'Space Grotesk', -apple-system, sans-serif !important;
    color: var(--text-primary);
}

section[data-testid="stSidebar"] {
    background-color: #080b13 !important;
    border-right: 1px solid rgba(0, 240, 255, 0.15) !important;
}

/* Typography */
h1, h2, h3, h4 {
    font-family: 'Orbitron', monospace !important;
    letter-spacing: 0.05em;
    color: #ffffff;
}

h1 {
    text-shadow: 0 0 16px rgba(0, 240, 255, 0.5);
}

/* Cards & Glassmorphism */
.cyber-card {
    background: var(--card-bg);
    border: 1px solid var(--border-glow);
    border-radius: 8px;
    padding: 1.25rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), inset 0 0 12px rgba(0, 240, 255, 0.03);
    backdrop-filter: blur(12px);
    margin-bottom: 1rem;
    position: relative;
}

.cyber-card::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 28px;
    height: 2px;
    background: var(--neon-cyan);
    box-shadow: 0 0 8px var(--neon-cyan);
}

/* Badges */
.cyber-badge {
    display: inline-block;
    padding: 3px 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    border-radius: 4px;
    text-transform: uppercase;
    background: rgba(0, 240, 255, 0.1);
    color: var(--neon-cyan);
    border: 1px solid rgba(0, 240, 255, 0.35);
}

.cyber-badge-green {
    background: rgba(0, 255, 157, 0.1);
    color: var(--neon-green);
    border: 1px solid rgba(0, 255, 157, 0.35);
}

.cyber-badge-purple {
    background: rgba(157, 78, 221, 0.15);
    color: #c77dff;
    border: 1px solid rgba(157, 78, 221, 0.4);
}

/* Lifecycle Pipeline Flow */
.pipeline-step {
    display: inline-flex;
    align-items: center;
    padding: 8px 14px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(15, 23, 42, 0.6);
    color: #94a3b8;
}

.pipeline-step.active {
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid var(--neon-cyan);
    color: #ffffff;
    box-shadow: 0 0 12px rgba(0, 240, 255, 0.25);
}

/* Metric Display */
.metric-val {
    font-family: 'Orbitron', monospace;
    font-size: 1.85rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.1;
    margin-top: 4px;
}

.metric-sub {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.delta-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--neon-green);
    margin-left: 6px;
}

/* Button */
.stButton > button {
    background: linear-gradient(135deg, rgba(0, 240, 255, 0.18), rgba(157, 78, 221, 0.25)) !important;
    border: 1px solid var(--neon-cyan) !important;
    color: #ffffff !important;
    font-family: 'Orbitron', monospace !important;
    font-weight: 700;
    letter-spacing: 0.12em;
    padding: 0.65rem 1.8rem;
    border-radius: 4px;
    box-shadow: 0 0 18px rgba(0, 240, 255, 0.3);
    transition: all 0.3s ease;
}

.stButton > button:hover {
    box-shadow: 0 0 28px rgba(0, 240, 255, 0.7);
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Helper Configuration Loader
# ==============================================================================
def load_config():
    config_file = "configs/sim_config.yaml"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    return {
        "num_rounds": 5,
        "num_clients_total": 5,
        "num_clients_per_round": 3,
        "learning_rate": 0.01,
        "batch_size": 16,
        "local_epochs": 3,
        "iid": True,
        "strategy": "FedAvg"
    }

cfg = load_config()

# ==============================================================================
# Sidebar Terminal Controls
# ==============================================================================
with st.sidebar:
    st.markdown('<span class="cyber-badge">TELEMETRY CONTROLLER</span>', unsafe_allow_html=True)
    st.markdown("### ⚙️ PARAMETERS")

    sim_rounds = st.slider("Federation Rounds", 1, 15, int(cfg.get("num_rounds", 5)))
    total_clients = st.slider("Total Clients (K)", 2, 8, int(cfg.get("num_clients_total", 5)))
    sampled_clients = st.slider("Sampled / Round (C × K)", 1, total_clients, min(int(cfg.get("num_clients_per_round", 3)), total_clients))

    st.markdown("---")
    st.markdown('<span class="cyber-badge cyber-badge-purple">SGD HYPERPARAMETERS</span>', unsafe_allow_html=True)

    lr = st.number_input("Learning Rate (η)", 0.001, 0.2, float(cfg.get("learning_rate", 0.01)), format="%.3f")
    epochs = st.slider("Local Epochs (E)", 1, 5, int(cfg.get("local_epochs", 3)))
    batch_size = st.selectbox("Batch Size (B)", [8, 16, 32, 64], index=1)
    is_iid = st.toggle("IID Partitioning", value=bool(cfg.get("iid", True)))

    st.markdown("---")
    strategy_choice = st.selectbox("Aggregation Strategy", ["FedAvg (Federated Averaging)", "TrimmedMean (Phase 2)", "Krum (Phase 2)"], index=0)


# ==============================================================================
# Header HUD
# ==============================================================================
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid rgba(0, 240, 255, 0.2); padding-bottom: 1rem; margin-bottom: 1.25rem;">
    <div>
        <div style="display: flex; gap: 8px; margin-bottom: 6px;">
            <span class="cyber-badge">CAPS // v1.2</span>
            <span class="cyber-badge cyber-badge-purple">FL SIMULATOR</span>
        </div>
        <h1 style="margin: 0; font-size: 2.2rem;">FEDERATED LEARNING COMMAND CONSOLE</h1>
        <div style="color: #64748b; font-size: 0.88rem; margin-top: 4px;">Decentralized Privacy-Preserving Neural Network Convergence &bull; FedAvg Protocol</div>
    </div>
    <div style="text-align: right;">
        <span class="cyber-badge cyber-badge-green">NETWORK: OPERATIONAL</span>
        <div style="color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 0.8rem; margin-top: 4px;">UCI Heart Disease (13 features) &bull; Seed: 42</div>
    </div>
</div>
""", unsafe_allow_html=True)

# DEPRECATION BANNER
st.warning("""
⚠️ **DEPRECATED DASHBOARD** - This is a visual demo with simulated data.

**Use the unified dashboard instead:**
```bash
bash run_unified.sh
```

The unified dashboard has:
- ✅ All visual design from this file
- ✅ Real DPS computation and self-healing
- ✅ Fixed bugs and complete features
- ✅ Actual simulation with recovery tracking
""")

st.markdown("---")


# ==============================================================================
# Telemetry Metric Ribbon
# ==============================================================================
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(f"""
    <div class="cyber-card">
        <div class="metric-sub">ACTIVE NODES</div>
        <div class="metric-val">{total_clients} <span style="font-size: 0.9rem; color: #00f0ff;">ONLINE</span></div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    participation_pct = int((sampled_clients / total_clients) * 100)
    st.markdown(f"""
    <div class="cyber-card">
        <div class="metric-sub">PARTICIPATION</div>
        <div class="metric-val">{participation_pct}% <span style="font-size: 0.85rem; color: #64748b;">({sampled_clients}/{total_clients})</span></div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="cyber-card">
        <div class="metric-sub">GLOBAL ACCURACY</div>
        <div class="metric-val">86.4% <span class="delta-tag">+28.2%</span></div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="cyber-card">
        <div class="metric-sub">GLOBAL LOSS</div>
        <div class="metric-val">0.281 <span class="delta-tag" style="color: #00f0ff;">-0.399</span></div>
    </div>
    """, unsafe_allow_html=True)

with m5:
    st.markdown(f"""
    <div class="cyber-card">
        <div class="metric-sub">DATA PRIVACY</div>
        <div class="metric-val" style="font-size: 1.25rem; padding-top: 0.4rem; color: #00ff9d;">ZERO LEAKAGE</div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# Round Lifecycle Stepper
# ==============================================================================
st.markdown("""
<div class="cyber-card" style="padding: 1rem 1.25rem;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
        <span style="font-family: 'Orbitron'; font-size: 0.85rem; color: #ffffff;">FEDERATED ROUND LIFECYCLE</span>
        <span class="cyber-badge cyber-badge-green">CURRENT PHASE: GLOBAL EVALUATION</span>
    </div>
    <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
        <div class="pipeline-step">1. Model Broadcast</div>
        <span style="color: #00f0ff;">&rarr;</span>
        <div class="pipeline-step">2. Local Client SGD</div>
        <span style="color: #00f0ff;">&rarr;</span>
        <div class="pipeline-step">3. Parameter Upload</div>
        <span style="color: #00f0ff;">&rarr;</span>
        <div class="pipeline-step">4. FedAvg Aggregation</div>
        <span style="color: #00f0ff;">&rarr;</span>
        <div class="pipeline-step active">5. Global Evaluation</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# Network Topology Visualizer Helper
# ==============================================================================
def create_topology_figure(num_nodes: int, active_nodes: list):
    fig = go.Figure()

    # Center Server Coordinates
    cx, cy = 0.0, 0.0

    # Client Node Angles
    angles = np.linspace(0, 2 * np.pi, num_nodes, endpoint=False)
    radius = 1.6

    client_x = [radius * np.cos(a) for a in angles]
    client_y = [radius * np.sin(a) for a in angles]

    # Draw connection lines
    for i in range(num_nodes):
        is_active = (i + 1) in active_nodes
        line_color = "#00f0ff" if is_active else "rgba(100, 116, 139, 0.3)"
        line_width = 2.5 if is_active else 1
        dash_style = "solid" if is_active else "dot"

        fig.add_trace(go.Scatter(
            x=[cx, client_x[i]],
            y=[cy, client_y[i]],
            mode="lines",
            line=dict(color=line_color, width=line_width, dash=dash_style),
            hoverinfo="none",
            showlegend=False
        ))

    # Draw Client Nodes
    client_colors = ["#00ff9d" if (i + 1) in active_nodes else "#475569" for i in range(num_nodes)]
    fig.add_trace(go.Scatter(
        x=client_x,
        y=client_y,
        mode="markers+text",
        marker=dict(size=32, color=client_colors, line=dict(color="#ffffff", width=1.5)),
        text=[f"Node #{i+1}" for i in range(num_nodes)],
        textposition="top center",
        textfont=dict(family="Orbitron", size=10, color="#ffffff"),
        name="Edge Clients",
        hovertext=[f"Client #{i+1}: {'AGGREGATED' if (i+1) in active_nodes else 'STANDBY'}" for i in range(num_nodes)],
        hoverinfo="text"
    ))

    # Draw Central Server Node
    fig.add_trace(go.Scatter(
        x=[cx], y=[cy],
        mode="markers+text",
        marker=dict(size=44, color="#00f0ff", symbol="hexagon", line=dict(color="#ffffff", width=2)),
        text=["SERVER"],
        textposition="bottom center",
        textfont=dict(family="Orbitron", size=11, color="#00f0ff"),
        name="Central Server",
        hovertext="FedAvg Aggregator Coordinator",
        hoverinfo="text"
    ))

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(13, 17, 27, 0.75)",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.2, 2.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.2, 2.2]),
        height=320
    )
    return fig


# ==============================================================================
# Simulation & Main Panels
# ==============================================================================
top_col1, top_col2 = st.columns([1.15, 1])

# Dynamic active node set
current_active = list(range(1, sampled_clients + 1))

with top_col1:
    st.markdown('<div class="cyber-card" style="padding-bottom: 0.5rem;"><span class="cyber-badge">FEDERATION TOPOLOGY</span>', unsafe_allow_html=True)
    topo_placeholder = st.empty()
    topo_placeholder.plotly_chart(create_topology_figure(total_clients, current_active), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with top_col2:
    st.markdown('<div class="cyber-card" style="padding-bottom: 0.5rem;"><span class="cyber-badge cyber-badge-green">CONVERGENCE TELEMETRY</span>', unsafe_allow_html=True)
    chart_placeholder = st.empty()

    # Pre-render initial trajectory
    dummy_rounds = list(range(1, sim_rounds + 1))
    dummy_acc = [min(0.56 + 0.31 * (1 - np.exp(-0.7 * r)), 0.88) for r in dummy_rounds]
    dummy_loss = [max(0.68 * np.exp(-0.5 * r) + 0.22, 0.25) for r in dummy_rounds]

    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
    fig_dual.add_trace(
        go.Scatter(x=dummy_rounds, y=dummy_acc, name="Accuracy", line=dict(color="#00f0ff", width=3, shape="spline"), mode="lines+markers"),
        secondary_y=False
    )
    fig_dual.add_trace(
        go.Scatter(x=dummy_rounds, y=dummy_loss, name="Loss", line=dict(color="#00ff9d", width=2.5, shape="spline", dash="dot"), mode="lines+markers"),
        secondary_y=True
    )
    fig_dual.update_layout(
        paper_bgcolor="rgba(13, 17, 27, 0.75)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk", color="#94a3b8"),
        margin=dict(l=40, r=40, t=30, b=30),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_dual.update_xaxes(title="Communication Round", gridcolor="rgba(0, 240, 255, 0.08)", dtick=1)
    fig_dual.update_yaxes(title="Global Accuracy", gridcolor="rgba(0, 240, 255, 0.08)", secondary_y=False)
    fig_dual.update_yaxes(title="Cross-Entropy Loss", gridcolor="rgba(0, 255, 157, 0.08)", secondary_y=True)
    chart_placeholder.plotly_chart(fig_dual, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# Simulation Action Trigger
# ==============================================================================
action_col1, action_col2 = st.columns([1, 2.5])
with action_col1:
    execute_sim = st.button("🚀 EXECUTE FEDERATED RUN", use_container_width=True)

with action_col2:
    status_msg = st.empty()
    status_msg.markdown('<div style="color: #64748b; font-family: JetBrains Mono; padding-top: 10px;">Ready for simulation. Select parameters and click Execute.</div>', unsafe_allow_html=True)

# Run animation when button is clicked
if execute_sim:
    status_msg.markdown('<span class="cyber-badge cyber-badge-green">EXECUTING REAL-TIME FEDERATED TRAINING...</span>', unsafe_allow_html=True)
    
    rounds_data, acc_data, loss_data = [], [], []

    for r in range(1, sim_rounds + 1):
        time.sleep(0.35)
        # Randomly sample active clients for this round
        active_ids = list(np.random.choice(range(1, total_clients + 1), sampled_clients, replace=False))
        topo_placeholder.plotly_chart(create_topology_figure(total_clients, active_ids), use_container_width=True)

        rounds_data.append(r)
        acc_data.append(min(0.55 + 0.32 * (1 - np.exp(-0.65 * r)) + np.random.normal(0, 0.01), 0.92))
        loss_data.append(max(0.69 * np.exp(-0.55 * r) + 0.23 + np.random.normal(0, 0.01), 0.22))

        # Update convergence plot dynamically
        fig_dyn = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dyn.add_trace(
            go.Scatter(x=rounds_data, y=acc_data, name="Accuracy", line=dict(color="#00f0ff", width=3, shape="spline"), mode="lines+markers"),
            secondary_y=False
        )
        fig_dyn.add_trace(
            go.Scatter(x=rounds_data, y=loss_data, name="Loss", line=dict(color="#00ff9d", width=2.5, shape="spline", dash="dot"), mode="lines+markers"),
            secondary_y=True
        )
        fig_dyn.update_layout(
            paper_bgcolor="rgba(13, 17, 27, 0.75)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Space Grotesk", color="#94a3b8"),
            margin=dict(l=40, r=40, t=30, b=30),
            height=320,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_dyn.update_xaxes(title="Round", dtick=1, gridcolor="rgba(0, 240, 255, 0.08)")
        fig_dyn.update_yaxes(title="Global Accuracy", secondary_y=False)
        fig_dyn.update_yaxes(title="Loss", secondary_y=True)
        chart_placeholder.plotly_chart(fig_dyn, use_container_width=True)

    status_msg.markdown(f'<span class="cyber-badge cyber-badge-green">CONVERGENCE ACHIEVED &bull; ROUNDS: {sim_rounds} &bull; FINAL ACC: {acc_data[-1]*100:.2f}%</span>', unsafe_allow_html=True)


# ==============================================================================
# Client Telemetry Table
# ==============================================================================
st.markdown("### 📡 PARTICIPATING NODE TELEMETRY")

records_per_node = int(242 / total_clients)
table_data = []

for i in range(1, total_clients + 1):
    is_active = i in current_active
    weight = (100.0 / sampled_clients) if is_active else 0.0
    table_data.append({
        "Node ID": f"Node #{i:02d}",
        "Status": "Aggregated" if is_active else "Standby",
        "Samples": f"{records_per_node} records",
        "Local Epochs": f"{epochs} epochs" if is_active else "-",
        "Local Loss": f"{0.25 + np.random.uniform(0.01, 0.06):.4f}" if is_active else "-",
        "Local Accuracy": f"{85.0 + np.random.uniform(1.0, 7.0):.1f}%" if is_active else "-",
        "FedAvg Share": f"{weight:.1f}%"
    })

df_telemetry = pd.DataFrame(table_data)
st.dataframe(df_telemetry, use_container_width=True, hide_index=True)
