"""
CAPS // ASH-FL Unified Dashboard
Combines Cyber HUD design (app.py) with real simulation functionality (dashboard_app.py)
"""

import os
import sys
import time
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure project root is available
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dashboard.simulator import DashboardSimulator
from dashboard.visualizations import (create_accuracy_chart, create_loss_chart, 
                                     create_dps_radar, create_trust_evolution, 
                                     create_aggregation_heatmap)
from dashboard.explanations import get_explanation_content


# ==============================================================================
# Network Topology Visualizer
# ==============================================================================
def create_topology_figure(num_nodes: int, active_nodes: list, malicious_nodes: list, results: dict):
    """
    Create network topology visualization showing central server and client nodes.
    
    Args:
        num_nodes: Total number of client nodes
        active_nodes: List of client IDs that are active (selected for this round)
        malicious_nodes: List of client IDs that are malicious
        results: Simulation results (for DPS-based coloring)
    
    Returns:
        Plotly figure
    """
    import plotly.graph_objects as go
    import numpy as np
    
    fig = go.Figure()

    # Center Server Coordinates
    cx, cy = 0.0, 0.0

    # Client Node Angles (arrange in circle)
    angles = np.linspace(0, 2 * np.pi, num_nodes, endpoint=False)
    radius = 1.6

    client_x = [radius * np.cos(a) for a in angles]
    client_y = [radius * np.sin(a) for a in angles]
    
    # Get DPS scores from final round for color intensity
    final_round = results['rounds'][-1]
    dps_scores = final_round.get('dps_scores', {})

    # Draw connection lines from server to each client
    for i in range(num_nodes):
        is_active = i in active_nodes
        is_malicious = i in malicious_nodes
        dps = dps_scores.get(i, 0.0)
        
        # Line style based on client status
        if is_malicious:
            line_color = f"rgba(255, 0, 110, {min(0.3 + dps * 0.7, 1.0)})"  # Red, intensity based on DPS
            line_width = 3 if is_active else 1.5
        elif is_active:
            line_color = "#00f0ff"  # Cyan for active honest
            line_width = 2.5
        else:
            line_color = "rgba(100, 116, 139, 0.3)"  # Gray for inactive
            line_width = 1
        
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
    client_colors = []
    client_sizes = []
    client_symbols = []
    hover_texts = []
    
    for i in range(num_nodes):
        is_active = i in active_nodes
        is_malicious = i in malicious_nodes
        dps = dps_scores.get(i, 0.0)
        
        if is_malicious:
            # Red shades for malicious (darker = higher DPS)
            intensity = min(0.5 + dps * 0.5, 1.0)
            client_colors.append(f"rgba(255, 0, 110, {intensity})")
            client_sizes.append(40 if is_active else 32)
            client_symbols.append("x")  # X symbol for malicious
            status = f"MALICIOUS (DPS: {dps:.3f})"
        elif is_active:
            client_colors.append("#00ff9d")  # Neon green for active honest
            client_sizes.append(36)
            client_symbols.append("circle")
            status = f"ACTIVE (DPS: {dps:.3f})"
        else:
            client_colors.append("#475569")  # Gray for standby
            client_sizes.append(28)
            client_symbols.append("circle")
            status = "STANDBY"
        
        hover_texts.append(f"<b>Client {i}</b><br>{status}")
    
    fig.add_trace(go.Scatter(
        x=client_x,
        y=client_y,
        mode="markers+text",
        marker=dict(
            size=client_sizes,
            color=client_colors,
            symbol=client_symbols,
            line=dict(color="#ffffff", width=1.5)
        ),
        text=[f"C{i}" for i in range(num_nodes)],
        textposition="top center",
        textfont=dict(family="Orbitron", size=10, color="#ffffff"),
        name="Clients",
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False
    ))

    # Draw Central Server Node
    fig.add_trace(go.Scatter(
        x=[cx], y=[cy],
        mode="markers+text",
        marker=dict(
            size=55,
            color="#00f0ff",
            symbol="hexagon",
            line=dict(color="#ffffff", width=2.5),
            opacity=0.9
        ),
        text=["SERVER"],
        textposition="bottom center",
        textfont=dict(family="Orbitron", size=12, color="#00f0ff", weight="bold"),
        name="Central Server",
        hovertext="<b>FedAvg Aggregator</b><br>Coordinates FL training",
        hoverinfo="text",
        showlegend=False
    ))

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(13, 17, 27, 0.75)",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.2, 2.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.2, 2.2]),
        height=400,
        font=dict(family="Space Grotesk", color="#94a3b8")
    )
    
    return fig


# ==============================================================================
# Page Configuration
# ==============================================================================
st.set_page_config(
    page_title="CAPS // ASH-FL Command Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    --neon-red: #ff006e;
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

.cyber-badge-red {
    background: rgba(255, 0, 110, 0.15);
    color: var(--neon-red);
    border: 1px solid rgba(255, 0, 110, 0.4);
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

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(13, 17, 27, 0.6);
    padding: 0.5rem;
    border-radius: 8px;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Orbitron', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
    background-color: transparent;
    border: 1px solid rgba(100, 116, 139, 0.3);
    border-radius: 4px;
    padding: 0.5rem 1rem;
}

.stTabs [aria-selected="true"] {
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid var(--neon-cyan);
    color: #ffffff;
    box-shadow: 0 0 12px rgba(0, 240, 255, 0.25);
}

/* DataFrames */
.stDataFrame {
    font-family: 'JetBrains Mono', monospace;
}

/* Malicious/Honest row highlighting */
.malicious-row {
    background-color: rgba(255, 0, 110, 0.1) !important;
}

.honest-row {
    background-color: rgba(0, 255, 157, 0.05) !important;
}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Session State Initialization
# ==============================================================================
if 'simulation_run' not in st.session_state:
    st.session_state.simulation_run = False
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None


# ==============================================================================
# Sidebar Terminal Controls
# ==============================================================================
def render_sidebar():
    """Render sidebar configuration panel."""
    with st.sidebar:
        st.markdown('<span class="cyber-badge">TELEMETRY CONTROLLER</span>', unsafe_allow_html=True)
        st.markdown("### ⚙️ SIMULATION PARAMETERS")

        num_clients = st.slider("Total Clients (K)", 3, 10, 5)
        num_rounds = st.slider("Federation Rounds", 5, 20, 15)  # Increased default from 8 to 15
        random_seed = st.number_input("Random Seed", 0, 9999, 42)

        st.markdown("---")
        st.markdown('<span class="cyber-badge cyber-badge-red">ATTACK CONFIGURATION</span>', unsafe_allow_html=True)
        
        enable_attack = st.checkbox("Enable Attacks", value=True)
        
        # Store per-client attack config
        client_attacks = {}
        scale_factor = 50.0
        
        if enable_attack:
            st.markdown("**🎯 Per-Client Attack Setup:**")
            
            # Quick presets
            preset = st.selectbox("Quick Preset", 
                                 ["Custom", "2 Scaling", "2 Label-Flip", "Mixed Attacks", "All Malicious"])
            
            if preset == "2 Scaling":
                for i in range(num_clients):
                    client_attacks[i] = "scaling" if i < 2 else "none"
            elif preset == "2 Label-Flip":
                for i in range(num_clients):
                    client_attacks[i] = "label_flip" if i < 2 else "none"
            elif preset == "Mixed Attacks":
                attacks = ["scaling", "label_flip", "sign_flip", "none", "none"]
                for i in range(num_clients):
                    client_attacks[i] = attacks[i] if i < len(attacks) else "none"
            elif preset == "All Malicious":
                for i in range(num_clients):
                    client_attacks[i] = "scaling"
            else:  # Custom
                for i in range(num_clients):
                    client_attacks[i] = st.selectbox(
                        f"Client {i}",
                        ["none", "scaling", "label_flip", "sign_flip", "backdoor"],
                        key=f"attack_{i}"
                    )
            
            # Attack parameters
            scale_factor = st.slider("Scaling Factor", 1.0, 100.0, 50.0, 5.0)
        
        else:
            for i in range(num_clients):
                client_attacks[i] = "none"

        st.markdown("---")
        st.markdown('<span class="cyber-badge cyber-badge-purple">SELF-HEALING</span>', unsafe_allow_html=True)
        
        enable_self_healing = st.checkbox("Enable Self-Healing", value=True)
        if enable_self_healing:
            dps_threshold = st.slider("DPS Threshold", 0.3, 1.0, 0.6, 0.05,
                                     help="Normalized DPS threshold [0,1]")
            st.info(f"💡 Threshold: {dps_threshold} (0.6=balanced, 0.7=strict)")
            recovery_rounds = st.slider("Recovery Rounds", 1, 5, 3)
        else:
            dps_threshold = 0.6
            recovery_rounds = 3

        st.markdown("---")
        
        # Run button
        col1, col2 = st.columns(2)
        with col1:
            run_clicked = st.button("🚀 EXECUTE", type="primary", use_container_width=True)
        with col2:
            reset_clicked = st.button("🔄 RESET", use_container_width=True)
        
        if run_clicked:
            run_simulation(num_clients, num_rounds, random_seed, client_attacks, 
                          scale_factor, enable_self_healing, dps_threshold, recovery_rounds)
        
        if reset_clicked:
            st.session_state.simulation_run = False
            st.session_state.simulation_results = None
            st.rerun()
        
        return num_clients, dps_threshold


def run_simulation(num_clients, num_rounds, random_seed, client_attacks, 
                   scale_factor, enable_self_healing, dps_threshold, recovery_rounds):
    """Run FL simulation with per-client attack configuration."""
    
    with st.spinner("🔄 Executing federated simulation..."):
        config = {
            'num_clients': num_clients,
            'num_rounds': num_rounds,
            'random_seed': random_seed,
            'enable_attack': any(a != "none" for a in client_attacks.values()),
            'client_attacks': client_attacks,
            'scale_factor': scale_factor,
            'enable_self_healing': enable_self_healing,
            'dps_threshold': dps_threshold,
            'recovery_rounds': recovery_rounds
        }
        
        # Run simulation
        simulator = DashboardSimulator(config)
        results = simulator.run_full_simulation()
        
        st.session_state.simulation_results = results
        st.session_state.simulation_run = True
        st.success("✅ Simulation complete!")
        st.rerun()


# ==============================================================================
# Main Content Area
# ==============================================================================
def render_header():
    """Render main header HUD."""
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid rgba(0, 240, 255, 0.2); padding-bottom: 1rem; margin-bottom: 1.25rem;">
        <div>
            <div style="display: flex; gap: 8px; margin-bottom: 6px;">
                <span class="cyber-badge">CAPS // v2.0</span>
                <span class="cyber-badge cyber-badge-purple">ASH-FL UNIFIED</span>
            </div>
            <h1 style="margin: 0; font-size: 2.2rem;">ADAPTIVE SELF-HEALING FL CONSOLE</h1>
            <div style="color: #64748b; font-size: 0.88rem; margin-top: 4px;">Real-Time Detection &bull; DPS Analysis &bull; Autonomous Recovery</div>
        </div>
        <div style="text-align: right;">
            <span class="cyber-badge cyber-badge-green">SYSTEM: OPERATIONAL</span>
            <div style="color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 0.8rem; margin-top: 4px;">UCI Heart Disease &bull; Real DPS (G/C/H/P)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_welcome_screen():
    """Show welcome screen before simulation runs."""
    st.markdown("""
    <div class="cyber-card" style="text-align: center; padding: 3rem;">
        <h2 style="color: var(--neon-cyan); font-size: 2rem; margin-bottom: 1rem;">🛡️ ASH-FL UNIFIED DASHBOARD</h2>
        <p style="font-size: 1.1rem; color: var(--text-muted); margin-bottom: 2rem;">
            Configure your simulation in the sidebar and click <strong style="color: var(--neon-cyan);">EXECUTE</strong> to begin.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="cyber-card">
            <h3 style="color: var(--neon-cyan); font-size: 1.1rem;">🔍 DETECTION</h3>
            <ul style="color: var(--text-muted); font-size: 0.9rem;">
                <li>Real-time DPS calculation</li>
                <li>5 detection signals (G,C,H,P,D)</li>
                <li>Per-client anomaly analysis</li>
                <li>Shadow validation (P signal)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="cyber-card">
            <h3 style="color: var(--neon-purple); font-size: 1.1rem;">🎯 ATTACKS</h3>
            <ul style="color: var(--text-muted); font-size: 0.9rem;">
                <li><strong>Per-client</strong> attack assignment</li>
                <li>4 attack types available</li>
                <li>Mix multiple attacks</li>
                <li>Configurable intensity</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="cyber-card">
            <h3 style="color: var(--neon-green); font-size: 1.1rem;">🛡️ SELF-HEALING</h3>
            <ul style="color: var(--text-muted); font-size: 0.9rem;">
                <li>Automatic attack detection</li>
                <li>Client quarantine (0.1x weight)</li>
                <li>Checkpoint restoration</li>
                <li>FSM-based recovery</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


def render_metrics_ribbon(results):
    """Render top metrics ribbon."""
    final_round = results['rounds'][-1]
    initial_round = results['rounds'][0]
    
    final_acc = final_round['metrics']['accuracy']
    initial_acc = initial_round['metrics']['accuracy']
    final_loss = final_round['metrics']['loss']
    initial_loss = initial_round['metrics']['loss']
    
    malicious_clients = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
    num_malicious = len(malicious_clients)
    num_clients = len(results['ground_truth'])
    
    # FIXED: Get recovery attempts from FSM controller state, not status message parsing
    recovery_attempts = results.get('recovery_attempts', 0)
    
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        acc_delta = final_acc - initial_acc
        delta_color = "var(--neon-green)" if acc_delta > 0 else "var(--neon-red)"
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">FINAL ACCURACY</div>
            <div class="metric-val">{final_acc:.1%} <span style="font-size: 0.75rem; color: {delta_color};">{acc_delta:+.1%}</span></div>
        </div>
        """, unsafe_allow_html=True)
    
    with m2:
        loss_delta = final_loss - initial_loss
        delta_color = "var(--neon-green)" if loss_delta < 0 else "var(--neon-red)"
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">FINAL LOSS</div>
            <div class="metric-val">{final_loss:.3f} <span style="font-size: 0.75rem; color: {delta_color};">{loss_delta:+.3f}</span></div>
        </div>
        """, unsafe_allow_html=True)
    
    with m3:
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">MALICIOUS NODES</div>
            <div class="metric-val">{num_malicious}/{num_clients} <span style="font-size: 0.85rem; color: var(--text-muted);">ACTIVE</span></div>
        </div>
        """, unsafe_allow_html=True)
    
    with m4:
        # Detection rate
        dps_threshold = results['config'].get('dps_threshold', 0.6)
        detected = sum(1 for cid in malicious_clients 
                      if final_round['dps_scores'].get(cid, 0) > dps_threshold)
        detection_rate = (detected / num_malicious * 100) if num_malicious > 0 else 0
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">DETECTION RATE</div>
            <div class="metric-val">{detection_rate:.0f}% <span style="font-size: 0.85rem; color: var(--text-muted);">({detected}/{num_malicious})</span></div>
        </div>
        """, unsafe_allow_html=True)
    
    with m5:
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">RECOVERY ATTEMPTS</div>
            <div class="metric-val" style="font-size: 1.6rem; color: var(--neon-purple);">{recovery_attempts} <span style="font-size: 0.75rem; color: var(--text-muted);">TRIGGERED</span></div>
        </div>
        """, unsafe_allow_html=True)


def render_overview_tab(results, dps_threshold, num_clients):
    """Overview tab with key metrics and charts."""
    st.markdown("### 📊 SIMULATION OVERVIEW")
    
    # Network Topology + Charts
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="cyber-card" style="padding-bottom: 0.5rem;"><span class="cyber-badge cyber-badge-cyan">FEDERATION TOPOLOGY</span>', unsafe_allow_html=True)
        
        # Get malicious clients for visualization
        malicious_clients = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
        
        # Get final round selected clients
        final_round = results['rounds'][-1]
        selected_clients = final_round.get('selected_clients', list(range(num_clients)))
        
        # Create topology figure
        fig_topo = create_topology_figure(num_clients, selected_clients, malicious_clients, results)
        st.plotly_chart(fig_topo, use_container_width=True, key="topology_chart")
        
        # Legend
        st.markdown("""
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: -10px; padding: 0 10px;">
            <strong>Legend:</strong><br/>
            🟢 Active Honest | ⚫ Standby | ❌ Malicious (intensity = DPS) | 🔷 Central Server
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cyber-card" style="padding-bottom: 0.5rem;"><span class="cyber-badge cyber-badge-green">ACCURACY TRAJECTORY</span>', unsafe_allow_html=True)
        fig = create_accuracy_chart(results)
        fig.update_layout(
            paper_bgcolor="rgba(13, 17, 27, 0.75)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Space Grotesk", color="#94a3b8"),
        )
        st.plotly_chart(fig, use_container_width=True, key="accuracy_chart_overview")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Loss chart full width
    st.markdown('<div class="cyber-card" style="padding-bottom: 0.5rem;"><span class="cyber-badge cyber-badge-green">LOSS CONVERGENCE</span>', unsafe_allow_html=True)
    fig = create_loss_chart(results)
    fig.update_layout(
        paper_bgcolor="rgba(13, 17, 27, 0.75)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk", color="#94a3b8"),
    )
    st.plotly_chart(fig, use_container_width=True, key="loss_chart_overview")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Ground truth table
    st.markdown("### 🎯 GROUND TRUTH & DETECTION STATUS")
    
    final_round = results['rounds'][-1]
    gt_data = []
    
    for cid in sorted(results['ground_truth'].keys()):
        is_mal = results['ground_truth'][cid]
        final_dps = final_round['dps_scores'].get(cid, 0)
        
        # Get attack type
        attack_type = "None"
        if is_mal and 'client_attacks' in results.get('config', {}):
            attack_type = results['config']['client_attacks'].get(cid, "unknown")
            attack_type = attack_type.replace("_", " ").title()
        
        status = "🔴 MALICIOUS" if is_mal else "✅ HONEST"
        detected = final_dps > dps_threshold
        detection_status = "✅ DETECTED" if (is_mal and detected) else ("❌ MISSED" if is_mal else "✅ CORRECT")
        
        gt_data.append({
            "Client ID": f"Client {cid}",
            "Status": status,
            "Attack Type": attack_type,
            "Final DPS": f"{final_dps:.3f}",
            "Detection": detection_status
        })
    
    gt_df = pd.DataFrame(gt_data)
    st.dataframe(gt_df, use_container_width=True, hide_index=True)


def render_dps_tab(results, dps_threshold):
    """DPS analysis tab."""
    st.markdown("### 🔍 DYNAMIC POISONING SCORE ANALYSIS")
    
    final_round = results['rounds'][-1]
    
    # DPS Deep Dive
    st.markdown("#### 📡 Signal Breakdown (Final Round)")
    
    dps_breakdown = []
    for cid in sorted(results['ground_truth'].keys()):
        is_mal = results['ground_truth'][cid]
        dps = final_round['dps_scores'].get(cid, 0)
        
        # Get individual signals
        G = final_round.get('G_scores', {}).get(cid, 0)
        C = final_round.get('C_scores', {}).get(cid, 0)
        H = final_round.get('H_scores', {}).get(cid, 0)
        P = final_round.get('P_scores', {}).get(cid, 0)
        D = final_round.get('D_scores', {}).get(cid, 0)
        
        status = "🔴 Malicious" if is_mal else "✅ Honest"
        flagged = "⚠️ FLAGGED" if dps > dps_threshold else "✓ NORMAL"
        
        dps_breakdown.append({
            "Client": f"Client {cid}",
            "Status": status,
            "DPS": f"{dps:.3f}",
            "G": f"{G:.3f}",
            "C": f"{C:.3f}",
            "H": f"{H:.3f}",
            "P": f"{P:.3f}",
            "D": f"{D:.3f}",
            "Flag": flagged
        })
    
    dps_df = pd.DataFrame(dps_breakdown)
    st.dataframe(dps_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Radar charts
    st.markdown("#### 🎯 Signal Radar (Malicious Clients)")
    
    malicious_clients = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
    
    if malicious_clients:
        cols = st.columns(min(3, len(malicious_clients)))
        for idx, cid in enumerate(malicious_clients[:3]):
            with cols[idx]:
                st.markdown(f'<div class="cyber-card" style="padding: 0.75rem;"><span class="cyber-badge cyber-badge-red">CLIENT {cid}</span>', unsafe_allow_html=True)
                fig = create_dps_radar(results, cid)
                fig.update_layout(
                    paper_bgcolor="rgba(13, 17, 27, 0.75)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Space Grotesk", color="#94a3b8", size=10),
                    height=250
                )
                st.plotly_chart(fig, use_container_width=True, key=f"radar_chart_client_{cid}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No malicious clients in this simulation.")


def render_selfhealing_tab(results):
    """Self-healing tab."""
    st.markdown("### 🛡️ SELF-HEALING MONITOR")
    
    # FSM state timeline
    st.markdown("#### 🔄 State Machine Timeline")
    
    timeline_data = []
    for round_info in results['rounds']:
        round_num = round_info['round']
        state = round_info.get('state', 'NORMAL')  # Fixed: was 'fsm_state'
        quarantined = round_info.get('quarantined', [])  # Fixed: was 'quarantined_clients'
        
        state_badge_colors = {
            'NORMAL': 'cyber-badge-green',
            'MONITOR': 'cyber-badge',
            'RECOVERY': 'cyber-badge-red',
            'VALIDATE': 'cyber-badge-purple',
            'RESUME': 'cyber-badge-green'
        }
        
        badge_class = state_badge_colors.get(state, 'cyber-badge')
        
        timeline_data.append({
            "Round": round_num,
            "FSM State": state,
            "Quarantined": len(quarantined),
            "Clients": ', '.join(map(str, quarantined)) if quarantined else '-'
        })
    
    timeline_df = pd.DataFrame(timeline_data)
    st.dataframe(timeline_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Trust evolution
    st.markdown("#### 📈 Trust Score Evolution")
    
    st.markdown('<div class="cyber-card" style="padding-bottom: 0.5rem;">', unsafe_allow_html=True)
    fig = create_trust_evolution(results)
    fig.update_layout(
        paper_bgcolor="rgba(13, 17, 27, 0.75)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk", color="#94a3b8"),
    )
    st.plotly_chart(fig, use_container_width=True, key="trust_evolution_chart")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary stats
    st.markdown("#### 📊 Recovery Summary")
    
    recovery_attempts = results.get('recovery_attempts', 0)
    checkpoint_count = results.get('checkpoint_count', 0)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">RECOVERY ATTEMPTS</div>
            <div class="metric-val" style="color: var(--neon-purple);">{recovery_attempts}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">CHECKPOINTS CREATED</div>
            <div class="metric-val" style="color: var(--neon-cyan);">{checkpoint_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        final_state = results['rounds'][-1].get('state', 'UNKNOWN')  # Fixed: was 'fsm_state'
        state_color = "var(--neon-green)" if final_state in ['NORMAL', 'RESUME'] else "var(--neon-red)"
        st.markdown(f"""
        <div class="cyber-card">
            <div class="metric-sub">FINAL STATE</div>
            <div class="metric-val" style="font-size: 1.3rem; color: {state_color};">{final_state}</div>
        </div>
        """, unsafe_allow_html=True)


def render_explanations_tab():
    """Educational explanations."""
    st.markdown("### 📚 EXPLANATIONS")
    
    explanations = get_explanation_content()
    
    for title, content in explanations.items():
        with st.expander(title):
            st.markdown(content)


# ==============================================================================
# Main Execution
# ==============================================================================
def main():
    """Main application entry point."""
    render_header()
    
    num_clients, dps_threshold = render_sidebar()
    
    if not st.session_state.simulation_run:
        render_welcome_screen()
    else:
        results = st.session_state.simulation_results
        
        # Metrics ribbon
        render_metrics_ribbon(results)
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 OVERVIEW",
            "🔍 DPS ANALYSIS", 
            "🛡️ SELF-HEALING",
            "📚 EXPLANATIONS"
        ])
        
        with tab1:
            render_overview_tab(results, dps_threshold, num_clients)
        
        with tab2:
            render_dps_tab(results, dps_threshold)
        
        with tab3:
            render_selfhealing_tab(results)
        
        with tab4:
            render_explanations_tab()


if __name__ == "__main__":
    main()
