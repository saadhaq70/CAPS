"""
ASH-FL Interactive Dashboard (REBUILT)
Complete Streamlit app with proper malicious client detection and per-client attack configuration.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from dashboard.simulator import DashboardSimulator
from dashboard.visualizations import (create_accuracy_chart, create_loss_chart, 
                                     create_dps_radar, create_trust_evolution, 
                                     create_aggregation_heatmap)
from dashboard.explanations import get_explanation_content

# Page config
st.set_page_config(
    page_title="ASH-FL Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        padding: 1rem 0;
    }
    .malicious-row {
        background-color: #ffebee !important;
    }
    .honest-row {
        background-color: #e8f5e9 !important;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'simulation_run' not in st.session_state:
    st.session_state.simulation_run = False
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None

def main():
    # Header
    st.markdown('<div class="main-header">🛡️ ASH-FL Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem;">Adaptive Self-Healing Federated Learning</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar Configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Basic settings
        st.markdown("### 🔧 Simulation")
        num_clients = st.slider("Number of Clients", 3, 10, 5)
        num_rounds = st.slider("Number of Rounds", 5, 20, 8)
        random_seed = st.number_input("Random Seed", 0, 9999, 42)
        
        st.markdown("---")
        
        # Per-client attack configuration
        st.markdown("### 🎯 Per-Client Attack Setup")
        enable_attack = st.checkbox("Enable Attacks", value=True)
        
        # Store per-client attack config
        client_attacks = {}
        if enable_attack:
            st.markdown("**Assign attacks to each client:**")
            
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
            st.markdown("**Attack Parameters:**")
            scale_factor = st.slider("Scaling Factor", 1.0, 100.0, 50.0, 5.0)
        
        else:
            for i in range(num_clients):
                client_attacks[i] = "none"
            scale_factor = 10.0
        
        st.markdown("---")
        
        # Self-healing
        st.markdown("### 🔄 Self-Healing")
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
        if st.button("🚀 RUN SIMULATION", type="primary", use_container_width=True):
            run_simulation(num_clients, num_rounds, random_seed, client_attacks, 
                          scale_factor, enable_self_healing, dps_threshold, recovery_rounds)
        
        if st.button("🔄 RESET", use_container_width=True):
            st.session_state.simulation_run = False
            st.session_state.simulation_results = None
            st.rerun()
    
    # Main content tabs
    if not st.session_state.simulation_run:
        show_welcome_screen()
    else:
        show_results_tabs(dps_threshold, num_clients)

def run_simulation(num_clients, num_rounds, random_seed, client_attacks, 
                   scale_factor, enable_self_healing, dps_threshold, recovery_rounds):
    """Run FL simulation with per-client attack configuration."""
    
    with st.spinner("🔄 Running simulation..."):
        config = {
            'num_clients': num_clients,
            'num_rounds': num_rounds,
            'random_seed': random_seed,
            'enable_attack': any(a != "none" for a in client_attacks.values()),
            'client_attacks': client_attacks,  # Per-client configuration
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

def show_welcome_screen():
    """Show welcome screen before simulation runs."""
    st.info("👈 Configure your simulation in the sidebar and click **RUN SIMULATION**")
    
    st.markdown("### 🎯 Key Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🔍 Detection")
        st.markdown("- Real-time DPS calculation")
        st.markdown("- 5 detection signals (G,C,H,P,D)")
        st.markdown("- Per-client analysis")
    
    with col2:
        st.markdown("#### 🎯 Attacks")
        st.markdown("- **Per-client** attack assignment")
        st.markdown("- 4 attack types available")
        st.markdown("- Mix multiple attacks")
    
    with col3:
        st.markdown("#### 🛡️ Self-Healing")
        st.markdown("- Automatic detection")
        st.markdown("- Client quarantine")
        st.markdown("- Checkpoint recovery")

def show_results_tabs(dps_threshold, num_clients):
    """Show results in tabbed interface."""
    results = st.session_state.simulation_results
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "🔍 DPS Analysis", 
        "🛡️ Self-Healing",
        "📚 Explanations"
    ])
    
    with tab1:
        show_overview_tab(results, dps_threshold, num_clients)
    
    with tab2:
        show_dps_tab(results, dps_threshold)
    
    with tab3:
        show_selfhealing_tab(results)
    
    with tab4:
        show_explanations_tab()

def show_overview_tab(results, dps_threshold, num_clients):
    """Overview tab with key metrics and charts."""
    st.markdown("### 📊 Simulation Overview")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    final_round = results['rounds'][-1]
    initial_round = results['rounds'][0]
    
    final_acc = final_round['metrics']['accuracy']
    initial_acc = initial_round['metrics']['accuracy']
    
    malicious_clients = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
    num_malicious = len(malicious_clients)
    
    # Count detected (DPS > threshold in final round)
    detected = sum(1 for cid in malicious_clients 
                  if final_round['dps_scores'].get(cid, 0) > dps_threshold)
    
    with col1:
        st.metric("Final Accuracy", f"{final_acc:.1%}", f"{final_acc - initial_acc:+.1%}")
    with col2:
        st.metric("Malicious Clients", f"{num_malicious}/{num_clients}")
    with col3:
        st.metric("Detected", f"{detected}/{num_malicious}", 
                 f"{(detected/num_malicious*100) if num_malicious > 0 else 0:.0f}%")
    with col4:
        st.metric("Recovery Attempts", results.get('recovery_attempts', 0))
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Accuracy Over Rounds")
        fig = create_accuracy_chart(results)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📉 Loss Over Rounds")
        fig = create_loss_chart(results)
        st.plotly_chart(fig, use_container_width=True)
    
    # Ground truth table with attack types
    st.markdown("### 🎯 Ground Truth & Attack Assignment")
    
    gt_data = []
    for cid in sorted(results['ground_truth'].keys()):
        is_mal = results['ground_truth'][cid]
        final_dps = final_round['dps_scores'].get(cid, 0)
        
        # Get attack type from config if available
        attack_type = "None (Honest)"
        if is_mal and 'client_attacks' in results.get('config', {}):
            attack_type = results['config']['client_attacks'].get(cid, "unknown")
            attack_type = attack_type.replace("_", " ").title()
        
        status = "🔴 Malicious" if is_mal else "✅ Honest"
        detected_status = "✅ Detected" if (is_mal and final_dps > dps_threshold) else ("❌ Missed" if is_mal else "✅ Correct")
        
        gt_data.append({
            "Client ID": cid,
            "Status": status,
            "Attack Type": attack_type,
            "Final DPS": f"{final_dps:.3f}",
            "Detection": detected_status
        })
    
    gt_df = pd.DataFrame(gt_data)
    st.dataframe(gt_df, use_container_width=True, hide_index=True)

def show_dps_tab(results, dps_threshold):
    """DPS analysis tab."""
    st.markdown("### 🔍 Dynamic Poisoning Score Analysis")
    
    st.markdown("""
    **DPS combines 5 signals (normalized to [0,1]):**
    - **G (0.33)**: Gradient deviation from median
    - **C (0.28)**: Cosine disagreement with consensus  
    - **H (0.22)**: History deviation from profile
    - **P (0.17)**: Performance impact on validation
    - **D (0.00)**: Data quality (disabled - privacy)
    """)
    
    st.markdown("---")
    
    # Round selector
    selected_round = st.selectbox("Select Round", 
                                 range(1, len(results['rounds']) + 1),
                                 index=len(results['rounds']) - 1)
    
    round_data = results['rounds'][selected_round - 1]
    
    # Build detailed table
    dps_data = []
    for cid in sorted(round_data['dps_scores'].keys()):
        is_mal = results['ground_truth'].get(cid, False)
        dps = round_data['dps_scores'][cid]
        
        G = round_data.get('G_scores', {}).get(cid, 0)
        C = round_data.get('C_scores', {}).get(cid, 0)
        H = round_data.get('H_scores', {}).get(cid, 0)
        P = round_data.get('P_scores', {}).get(cid, 0)
        D = round_data.get('D_scores', {}).get(cid, 0)
        
        trust = round_data['trust_scores'].get(cid, 1.0)
        weight = round_data['aggregation_weights'].get(cid, 0.0)
        
        is_quarantined = cid in round_data.get('quarantined', [])
        
        status = "🔴 Malicious" if is_mal else "✅ Honest"
        action = "🔒 Quarantined" if is_quarantined else ("⚠️ Suspicious" if dps > dps_threshold else "✅ Normal")
        
        dps_data.append({
            "Client": cid,
            "Status": status,
            "G": f"{G:.3f}",
            "C": f"{C:.3f}",
            "H": f"{H:.3f}",
            "P": f"{P:.3f}",
            "D": f"{D:.3f}",
            "DPS": f"{dps:.3f}",
            "Trust": f"{trust:.3f}",
            "Weight": f"{weight:.3f}",
            "Action": action
        })
    
    dps_df = pd.DataFrame(dps_data)
    
    st.markdown(f"#### Round {selected_round} - Client Scores")
    st.dataframe(dps_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Radar chart for selected client
    st.markdown("#### 📡 Signal Breakdown")
    selected_client = st.selectbox("Select Client", sorted(round_data['dps_scores'].keys()))
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        client_row = dps_df[dps_df['Client'] == selected_client].iloc[0]
        fig = create_dps_radar({
            'G': float(client_row['G']),
            'C': float(client_row['C']),
            'H': float(client_row['H']),
            'P': float(client_row['P']),
            'D': float(client_row['D'])
        }, client_row['Status'] == '🔴 Malicious')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown(f"##### Client {selected_client}")
        st.markdown(f"**Status:** {client_row['Status']}")
        st.markdown(f"**DPS:** {client_row['DPS']} (threshold: {dps_threshold:.2f})")
        st.markdown(f"**Trust:** {client_row['Trust']}")
        st.markdown(f"**Action:** {client_row['Action']}")
        
        st.markdown("**Individual Signals:**")
        st.markdown(f"- G (Gradient): {client_row['G']}")
        st.markdown(f"- C (Cosine): {client_row['C']}")
        st.markdown(f"- H (History): {client_row['H']}")
        st.markdown(f"- P (Performance): {client_row['P']}")
        st.markdown(f"- D (Data): {client_row['D']}")

def show_selfhealing_tab(results):
    """Self-healing monitoring tab."""
    st.markdown("### 🛡️ Self-Healing Monitor")
    
    # Current state
    final_round = results['rounds'][-1]
    current_state = final_round.get('state', 'normal').upper()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current State", current_state)
    with col2:
        st.metric("Recovery Attempts", results.get('recovery_attempts', 0))
    with col3:
        checkpoints = sum(1 for e in results.get('events', []) if 'checkpoint' in e.get('message', '').lower())
        st.metric("Checkpoints Saved", checkpoints)
    with col4:
        quarantined = len(final_round.get('quarantined', []))
        st.metric("Quarantined Clients", quarantined)
    
    st.markdown("---")
    
    # State timeline
    st.markdown("#### 📅 State Timeline")
    state_data = []
    for r in results['rounds']:
        state_data.append({
            'Round': r['round'],
            'State': r.get('state', 'normal').upper(),
            'Max DPS': max(r['dps_scores'].values()) if r['dps_scores'] else 0,
            'Accuracy': r['metrics']['accuracy'],
            'Quarantined': len(r.get('quarantined', []))
        })
    
    state_df = pd.DataFrame(state_data)
    
    # State chart
    fig = go.Figure()
    
    # Map states to numbers for plotting
    state_map = {'NORMAL': 0, 'MONITOR': 1, 'RECOVERY': 2, 'VALIDATE': 3, 'RESUME': 1}
    state_df['State_Num'] = state_df['State'].map(state_map)
    
    fig.add_trace(go.Scatter(
        x=state_df['Round'],
        y=state_df['State_Num'],
        mode='lines+markers',
        name='State',
        line=dict(color='blue', width=3),
        marker=dict(size=10)
    ))
    
    fig.update_layout(
        title="State Machine Transitions",
        xaxis_title="Round",
        yaxis=dict(
            tickmode='array',
            tickvals=[0, 1, 2, 3],
            ticktext=['NORMAL', 'MONITOR/RESUME', 'RECOVERY', 'VALIDATE']
        ),
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.dataframe(state_df, use_container_width=True, hide_index=True)
    
    # Events log
    if results.get('events'):
        st.markdown("#### 📜 Event Log")
        for event in results['events']:
            st.markdown(f"- **Round {event.get('round', '?')}**: {event.get('message', '')}")
    
    # Quarantined clients over time
    st.markdown("#### 🔒 Quarantined Clients Over Time")
    quarantine_data = []
    for r in results['rounds']:
        for cid in range(max(results['ground_truth'].keys()) + 1):
            quarantine_data.append({
                'Round': r['round'],
                'Client': cid,
                'Quarantined': 1 if cid in r.get('quarantined', []) else 0
            })
    
    if quarantine_data:
        q_df = pd.DataFrame(quarantine_data)
        fig = px.density_heatmap(
            q_df, x='Round', y='Client', z='Quarantined',
            color_continuous_scale=['green', 'red'],
            title="Quarantine Status (Red = Quarantined)"
        )
        st.plotly_chart(fig, use_container_width=True)

def show_explanations_tab():
    """Educational explanations."""
    st.markdown("### 📚 Explanations")
    
    explanations = get_explanation_content()
    
    for title, content in explanations.items():
        with st.expander(title):
            st.markdown(content)

if __name__ == "__main__":
    main()
