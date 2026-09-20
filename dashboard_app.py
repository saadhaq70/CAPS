"""
ASH-FL Interactive Dashboard
Complete Streamlit application for visualizing federated learning with attacks and self-healing.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import time

# Import dashboard modules
from dashboard.simulator import DashboardSimulator
from dashboard.dps_calculator import DPSCalculator
from dashboard.visualizations import create_accuracy_chart, create_loss_chart, create_dps_radar, create_trust_evolution, create_aggregation_heatmap
from dashboard.explanations import get_explanation_content

# Page configuration
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
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        padding: 0.5rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .malicious-client {
        background-color: #ffebee !important;
        font-weight: bold;
    }
    .healthy-client {
        background-color: #e8f5e9 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'simulation_run' not in st.session_state:
    st.session_state.simulation_run = False
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None
if 'current_round' not in st.session_state:
    st.session_state.current_round = 0
if 'step_by_step' not in st.session_state:
    st.session_state.step_by_step = False

def reset_simulation():
    """Reset all simulation state."""
    st.session_state.simulation_run = False
    st.session_state.simulation_results = None
    st.session_state.current_round = 0
    st.session_state.step_by_step = False

def main():
    """Main dashboard application."""
    
    # Header
    st.markdown('<div class="main-header">🛡️ ASH-FL Interactive Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #7f8c8d;">Adaptive Self-Healing Federated Learning with Attack Detection</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=80)
        st.markdown("## ⚙️ Configuration")
        
        # Simulation parameters
        st.markdown("### 🔧 Simulation Setup")
        num_clients = st.slider("Number of Clients", min_value=3, max_value=10, value=5, help="Total number of federated learning clients")
        num_rounds = st.slider("Number of Rounds", min_value=5, max_value=20, value=10, help="Training rounds to simulate")
        random_seed = st.number_input("Random Seed", min_value=0, max_value=9999, value=42, help="For reproducibility")
        
        st.markdown("---")
        
        # Attack configuration
        st.markdown("### 🎯 Attack Configuration")
        enable_attack = st.checkbox("Enable Attack", value=True, help="Inject malicious clients")
        
        attack_type = st.selectbox(
            "Attack Type",
            ["label_flip", "sign_flip", "scaling", "backdoor"],
            disabled=not enable_attack,
            help="Type of poisoning attack to inject"
        )
        
        num_malicious = st.slider(
            "Malicious Clients",
            min_value=0,
            max_value=num_clients-1,
            value=min(2, num_clients-1),
            disabled=not enable_attack,
            help="Number of malicious clients"
        )
        
        if attack_type == "scaling":
            scale_factor = st.slider("Scale Factor", min_value=1.0, max_value=100.0, value=50.0, step=5.0,
                                    disabled=not enable_attack)
        else:
            scale_factor = 10.0
        
        st.markdown("---")
        
        # Self-healing configuration
        st.markdown("### 🔄 Self-Healing")
        enable_self_healing = st.checkbox("Enable Self-Healing", value=True, help="Activate adaptive recovery system")
        
        if enable_self_healing:
            dps_threshold = st.slider("DPS Threshold", min_value=0.5, max_value=5.0, value=2.0, step=0.1,
                                     help="Threshold for flagging suspicious clients")
            recovery_rounds = st.slider("Recovery Rounds", min_value=1, max_value=5, value=3,
                                       help="Rounds to retrain during recovery")
        else:
            dps_threshold = 2.0
            recovery_rounds = 3
        
        st.markdown("---")
        
        # Execution mode
        st.markdown("### ▶️ Execution")
        execution_mode = st.radio("Mode", ["Full Run", "Step-by-Step"], help="Run all rounds or step through one at a time")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            run_button = st.button("🚀 Run", type="primary", use_container_width=True)
        with col2:
            reset_button = st.button("🔄 Reset", use_container_width=True)
        
        if reset_button:
            reset_simulation()
            st.rerun()
    
    # Main content - Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview",
        "🎯 Attack & Performance",
        "🔍 DPS Deep Dive",
        "🤝 Trust & Aggregation",
        "🛡️ Self-Healing Monitor",
        "📚 Explanations"
    ])
    
    # Run simulation when button clicked
    if run_button:
        st.session_state.step_by_step = (execution_mode == "Step-by-Step")
        
        with st.spinner("Initializing simulation..."):
            # Create configuration
            config = {
                'num_clients': num_clients,
                'num_rounds': num_rounds,
                'random_seed': random_seed,
                'enable_attack': enable_attack,
                'attack_type': attack_type,
                'num_malicious': num_malicious,
                'scale_factor': scale_factor,
                'enable_self_healing': enable_self_healing,
                'dps_threshold': dps_threshold,
                'recovery_rounds': recovery_rounds
            }
            
            # Run simulation
            simulator = DashboardSimulator(config)
            
            if st.session_state.step_by_step:
                # Initialize for step-by-step
                st.session_state.simulator = simulator
                st.session_state.current_round = 1
                results = simulator.run_single_round(1)
                st.session_state.simulation_results = results
            else:
                # Full run with progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = simulator.run_full_simulation(
                    progress_callback=lambda r, total: (
                        progress_bar.progress(r / total),
                        status_text.text(f"Running round {r}/{total}...")
                    )
                )
                
                progress_bar.progress(1.0)
                status_text.text("✅ Simulation complete!")
                st.session_state.simulation_results = results
            
            st.session_state.simulation_run = True
            time.sleep(0.5)
            st.rerun()
    
    # Step-by-step controls
    if st.session_state.step_by_step and st.session_state.simulation_run:
        st.markdown("### 🎮 Step-by-Step Control")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            subcol1, subcol2, subcol3 = st.columns(3)
            with subcol1:
                if st.button("⏮️ Previous", disabled=st.session_state.current_round <= 1):
                    st.session_state.current_round -= 1
                    st.rerun()
            with subcol2:
                st.markdown(f"<div style='text-align: center; padding: 10px; font-size: 1.2rem; font-weight: bold;'>Round {st.session_state.current_round}/{num_rounds}</div>", unsafe_allow_html=True)
            with subcol3:
                if st.button("Next ⏭️", disabled=st.session_state.current_round >= num_rounds):
                    st.session_state.current_round += 1
                    # Run next round
                    results = st.session_state.simulator.run_single_round(st.session_state.current_round)
                    st.session_state.simulation_results = results
                    st.rerun()
        st.markdown("---")
    
    # Tab 1: Overview
    with tab1:
        if not st.session_state.simulation_run:
            st.info("👈 Configure your simulation in the sidebar and click **Run** to start!")
            
            # Show example visualization
            st.markdown("### 📈 What You'll See:")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Global Accuracy", "85.3%", "+12.1%")
            with col2:
                st.metric("Detected Attacks", "3 clients", "")
            with col3:
                st.metric("Recovery Success", "100%", "+2 rounds")
            
            st.markdown("### 🎯 Dashboard Features:")
            features = [
                "**Real-time FL simulation** with UCI Heart Disease dataset",
                "**4 attack types**: Label Flip, Sign Flip, Scaling, Backdoor",
                "**Dynamic Poisoning Score (DPS)** calculation with G, C, H, P, D signals",
                "**Self-healing recovery** with automatic checkpoint restoration",
                "**Interactive visualizations** for every metric and signal",
                "**Educational explanations** of all algorithms and formulas"
            ]
            for feature in features:
                st.markdown(f"- {feature}")
        
        else:
            results = st.session_state.simulation_results
            
            st.markdown("### 📊 Simulation Overview")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            final_round = len(results['rounds']) - 1
            final_acc = results['rounds'][final_round]['metrics']['accuracy']
            initial_acc = results['rounds'][0]['metrics']['accuracy']
            acc_improvement = final_acc - initial_acc
            
            malicious_ids = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
            detected_count = sum(1 for cid in malicious_ids 
                               if results['rounds'][final_round]['dps_scores'][cid] > dps_threshold)
            
            with col1:
                st.metric("Final Accuracy", f"{final_acc:.1%}", f"{acc_improvement:+.1%}")
            with col2:
                st.metric("Malicious Clients", f"{len(malicious_ids)}/{num_clients}")
            with col3:
                st.metric("Detected", f"{detected_count}/{len(malicious_ids)}")
            with col4:
                recovery_attempts = results.get('recovery_attempts', 0)
                st.metric("Recovery Attempts", recovery_attempts)
            
            st.markdown("---")
            
            # Quick charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📈 Accuracy Trajectory")
                fig = create_accuracy_chart(results)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 📉 Loss Trajectory")
                fig = create_loss_chart(results)
                st.plotly_chart(fig, use_container_width=True)
            
            # Ground truth table
            st.markdown("### 🎯 Ground Truth")
            gt_df = pd.DataFrame([
                {"Client ID": cid, "Status": "🔴 Malicious" if is_mal else "✅ Honest"}
                for cid, is_mal in sorted(results['ground_truth'].items())
            ])
            st.dataframe(gt_df, use_container_width=True, hide_index=True)
    
    # Tab 2: Attack & Performance
    with tab2:
        if not st.session_state.simulation_run:
            st.info("Run a simulation to see attack and performance analysis!")
        else:
            results = st.session_state.simulation_results
            
            st.markdown("### 🎯 Attack & Performance Analysis")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            rounds_data = results['rounds']
            accuracies = [r['metrics']['accuracy'] for r in rounds_data]
            losses = [r['metrics']['loss'] for r in rounds_data]
            
            with col1:
                st.markdown("#### Initial Performance")
                st.metric("Accuracy", f"{accuracies[0]:.3f}")
                st.metric("Loss", f"{losses[0]:.3f}")
            
            with col2:
                st.markdown("#### Final Performance")
                st.metric("Accuracy", f"{accuracies[-1]:.3f}", f"{accuracies[-1] - accuracies[0]:+.3f}")
                st.metric("Loss", f"{losses[-1]:.3f}", f"{losses[-1] - losses[0]:+.3f}")
            
            with col3:
                st.markdown("#### Best Performance")
                best_acc = max(accuracies)
                best_acc_round = accuracies.index(best_acc) + 1
                st.metric("Peak Accuracy", f"{best_acc:.3f}", f"Round {best_acc_round}")
                worst_loss = min(losses)
                st.metric("Lowest Loss", f"{worst_loss:.3f}")
            
            st.markdown("---")
            
            # Detailed charts
            st.markdown("### 📊 Performance Over Time")
            
            fig = create_accuracy_chart(results, detailed=True)
            st.plotly_chart(fig, use_container_width=True)
            
            fig = create_loss_chart(results, detailed=True)
            st.plotly_chart(fig, use_container_width=True)
            
            # Attack impact analysis
            if enable_attack:
                st.markdown("### 🔴 Attack Impact")
                
                malicious_ids = [cid for cid, is_mal in results['ground_truth'].items() if is_mal]
                
                impact_data = []
                for round_idx, round_data in enumerate(rounds_data):
                    dps_scores = round_data['dps_scores']
                    avg_mal_dps = np.mean([dps_scores[cid] for cid in malicious_ids if cid in dps_scores])
                    honest_ids = [cid for cid in dps_scores.keys() if cid not in malicious_ids]
                    avg_honest_dps = np.mean([dps_scores[cid] for cid in honest_ids]) if honest_ids else 0
                    
                    impact_data.append({
                        'Round': round_idx + 1,
                        'Malicious Avg DPS': avg_mal_dps,
                        'Honest Avg DPS': avg_honest_dps
                    })
                
                impact_df = pd.DataFrame(impact_data)
                
                fig = px.line(impact_df, x='Round', y=['Malicious Avg DPS', 'Honest Avg DPS'],
                            title="DPS Comparison: Malicious vs Honest Clients",
                            labels={'value': 'Average DPS', 'variable': 'Client Type'},
                            color_discrete_map={'Malicious Avg DPS': 'red', 'Honest Avg DPS': 'green'})
                fig.add_hline(y=dps_threshold, line_dash="dash", line_color="orange",
                            annotation_text="DPS Threshold")
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: DPS Deep Dive
    with tab3:
        if not st.session_state.simulation_run:
            st.info("Run a simulation to explore DPS calculations!")
        else:
            results = st.session_state.simulation_results
            
            st.markdown("### 🔍 Dynamic Poisoning Score (DPS) Deep Dive")
            st.markdown("**DPS combines multiple signals to detect malicious behavior:**")
            st.markdown("- **G**: Gradient deviation (distance from median)")
            st.markdown("- **C**: Cosine disagreement (angle from consensus)")
            st.markdown("- **H**: History deviation (change from profile)")
            st.markdown("- **P**: Performance impact (validation effect)")
            st.markdown("- **D**: Data quality score")
            
            st.markdown("---")
            
            # Round selector
            if st.session_state.step_by_step:
                selected_round = st.session_state.current_round
            else:
                selected_round = st.selectbox("Select Round", range(1, len(results['rounds']) + 1),
                                             index=len(results['rounds']) - 1)
            
            round_data = results['rounds'][selected_round - 1]
            
            # Build DPS table
            dps_table_data = []
            for cid in sorted(round_data['dps_scores'].keys()):
                is_malicious = results['ground_truth'].get(cid, False)
                dps_score = round_data['dps_scores'][cid]
                trust_score = round_data['trust_scores'].get(cid, 1.0)
                agg_weight = round_data['aggregation_weights'].get(cid, 0.0)
                
                # Get signal components (simulated for now)
                G = round_data.get('G_scores', {}).get(cid, dps_score * 0.3)
                C = round_data.get('C_scores', {}).get(cid, dps_score * 0.25)
                H = round_data.get('H_scores', {}).get(cid, dps_score * 0.2)
                P = round_data.get('P_scores', {}).get(cid, dps_score * 0.15)
                D = round_data.get('D_scores', {}).get(cid, dps_score * 0.1)
                
                # Determine action
                if dps_score > dps_threshold:
                    action = "⚠️ Suspicious"
                elif round_data.get('state', 'NORMAL') == 'RECOVERY' and dps_score > dps_threshold * 0.7:
                    action = "🔒 Quarantined"
                else:
                    action = "✅ Normal"
                
                dps_table_data.append({
                    'Client ID': cid,
                    'Status': '🔴 Malicious' if is_malicious else '✅ Honest',
                    'G': f"{G:.3f}",
                    'C': f"{C:.3f}",
                    'H': f"{H:.3f}",
                    'P': f"{P:.3f}",
                    'D': f"{D:.3f}",
                    'DPS': f"{dps_score:.3f}",
                    'Trust': f"{trust_score:.3f}",
                    'Weight': f"{agg_weight:.3f}",
                    'Action': action
                })
            
            dps_df = pd.DataFrame(dps_table_data)
            
            # Display table with styling
            st.markdown(f"#### Round {selected_round} - Client Analysis")
            st.dataframe(
                dps_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Client ID": st.column_config.NumberColumn("Client ID", width="small"),
                    "DPS": st.column_config.TextColumn("DPS", width="small"),
                    "Trust": st.column_config.TextColumn("Trust", width="small"),
                    "Weight": st.column_config.TextColumn("Weight", width="small"),
                }
            )
            
            st.markdown("---")
            
            # Radar chart for selected client
            st.markdown("#### 📡 Signal Breakdown by Client")
            selected_client = st.selectbox("Select Client for Detailed View",
                                          sorted(round_data['dps_scores'].keys()))
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Radar chart
                client_row = dps_df[dps_df['Client ID'] == selected_client].iloc[0]
                fig = create_dps_radar(
                    {
                        'G': float(client_row['G']),
                        'C': float(client_row['C']),
                        'H': float(client_row['H']),
                        'P': float(client_row['P']),
                        'D': float(client_row['D'])
                    },
                    client_row['Status'] == '🔴 Malicious'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown(f"##### Client {selected_client} Details")
                st.markdown(f"**Status:** {client_row['Status']}")
                st.markdown(f"**DPS:** {client_row['DPS']}")
                st.markdown(f"**Trust:** {client_row['Trust']}")
                st.markdown(f"**Action:** {client_row['Action']}")
                
                st.markdown("---")
                st.markdown("**Signal Explanations:**")
                with st.expander("🔹 G - Gradient Deviation"):
                    st.markdown("""
                    Measures how far this client's update is from the median update.
                    - **Formula**: `G = |update - median| / MAD`
                    - **High G**: Update is an outlier
                    - **Threshold**: Typically > 2.0 indicates anomaly
                    """)
                
                with st.expander("🔹 C - Cosine Disagreement"):
                    st.markdown("""
                    Measures angular distance from the consensus direction.
                    - **Formula**: `C = 1 - cosine_similarity(update, median)`
                    - **High C**: Update points in wrong direction
                    - **Range**: 0 (perfect agreement) to 2 (opposite direction)
                    """)
                
                with st.expander("🔹 H - History Deviation"):
                    st.markdown("""
                    Compares current update to client's historical profile.
                    - **Formula**: `H = |current - EMA(history)| / std(history)`
                    - **High H**: Behavior changed suddenly
                    - **Adaptive**: Profile updates over time
                    """)
                
                with st.expander("🔹 P - Performance Impact"):
                    st.markdown("""
                    Estimates effect on global model accuracy.
                    - **Method**: Shadow validation on held-out set
                    - **High P**: Update degrades model
                    - **Costly**: Only computed when suspicious
                    """)
                
                with st.expander("🔹 D - Data Quality"):
                    st.markdown("""
                    Assesses local data distribution quality.
                    - **Factors**: Class balance, feature variance, sample count
                    - **Low D**: Poor quality data
                    - **Used**: To weight other signals
                    """)
    
    # Tab 4: Trust & Aggregation
    with tab4:
        if not st.session_state.simulation_run:
            st.info("Run a simulation to see trust evolution!")
        else:
            results = st.session_state.simulation_results
            
            st.markdown("### 🤝 Trust & Aggregation Analysis")
            
            st.markdown("""
            **Aggregation Weight Formula:**
            
            $$a_i = n_i \\times R_i^\\gamma \\times (1 - DPS_i)^\\eta$$
            
            Where:
            - $n_i$: Number of samples from client $i$
            - $R_i$: Trust (reputation) score
            - $DPS_i$: Dynamic Poisoning Score
            - $\\gamma$: Trust sensitivity (default: 2.0)
            - $\\eta$: DPS penalty (default: 1.5)
            """)
            
            st.markdown("---")
            
            # Trust evolution chart
            st.markdown("#### 📈 Trust Score Evolution")
            fig = create_trust_evolution(results)
            st.plotly_chart(fig, use_container_width=True)
            
            # Aggregation weights heatmap
            st.markdown("#### 🎨 Aggregation Weights Heatmap")
            fig = create_aggregation_heatmap(results)
            st.plotly_chart(fig, use_container_width=True)
            
            # Final trust scores
            st.markdown("#### 🏆 Final Trust Scores")
            final_round = results['rounds'][-1]
            trust_data = []
            for cid in sorted(final_round['trust_scores'].keys()):
                trust_data.append({
                    'Client ID': cid,
                    'Status': '🔴 Malicious' if results['ground_truth'].get(cid, False) else '✅ Honest',
                    'Trust Score': f"{final_round['trust_scores'][cid]:.4f}",
                    'Final DPS': f"{final_round['dps_scores'][cid]:.3f}",
                    'Final Weight': f"{final_round['aggregation_weights'].get(cid, 0.0):.4f}"
                })
            
            trust_df = pd.DataFrame(trust_data)
            st.dataframe(trust_df, use_container_width=True, hide_index=True)
    
    # Tab 5: Self-Healing Monitor
    with tab5:
        if not st.session_state.simulation_run:
            st.info("Run a simulation with self-healing enabled to see recovery in action!")
        else:
            results = st.session_state.simulation_results
            
            st.markdown("### 🛡️ Self-Healing Monitor")
            
            if not enable_self_healing:
                st.warning("Self-healing is disabled for this simulation.")
            else:
                # Current state
                current_state = results['rounds'][-1].get('state', 'NORMAL')
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Current State", current_state)
                with col2:
                    st.metric("Recovery Attempts", results.get('recovery_attempts', 0))
                with col3:
                    checkpoints = results.get('checkpoint_count', 0)
                    st.metric("Checkpoints Saved", checkpoints)
                with col4:
                    quarantined = sum(1 for r in results['rounds'][-1].get('quarantined', []))
                    st.metric("Quarantined Clients", quarantined)
                
                st.markdown("---")
                
                # State timeline
                st.markdown("#### 📅 State Timeline")
                timeline_data = []
                for round_idx, round_data in enumerate(results['rounds']):
                    state = round_data.get('state', 'NORMAL')
                    timeline_data.append({
                        'Round': round_idx + 1,
                        'State': state,
                        'Accuracy': round_data['metrics']['accuracy'],
                        'Avg DPS': np.mean(list(round_data['dps_scores'].values()))
                    })
                
                timeline_df = pd.DataFrame(timeline_data)
                
                fig = px.line(timeline_df, x='Round', y='Accuracy',
                            title="Accuracy with State Annotations",
                            markers=True)
                
                # Add state change markers
                state_changes = timeline_df[timeline_df['State'] != 'NORMAL']
                if not state_changes.empty:
                    fig.add_scatter(x=state_changes['Round'], y=state_changes['Accuracy'],
                                  mode='markers', marker=dict(size=15, color='red', symbol='star'),
                                  name='State Change')
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Event log
                st.markdown("#### 📝 Event Log")
                events = results.get('events', [])
                if events:
                    for event in events:
                        st.markdown(f"- **Round {event['round']}**: {event['message']}")
                else:
                    st.info("No recovery events in this simulation.")
                
                # Health metrics
                st.markdown("#### 💊 Health Metrics")
                health_data = []
                for round_idx, round_data in enumerate(results['rounds']):
                    dps_scores = list(round_data['dps_scores'].values())
                    suspicious_count = sum(1 for dps in dps_scores if dps > dps_threshold)
                    
                    health_data.append({
                        'Round': round_idx + 1,
                        'Accuracy': round_data['metrics']['accuracy'],
                        'Avg DPS': np.mean(dps_scores),
                        'Max DPS': max(dps_scores),
                        'Suspicious Fraction': suspicious_count / len(dps_scores) if dps_scores else 0
                    })
                
                health_df = pd.DataFrame(health_data)
                
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Accuracy', 'Average DPS', 'Max DPS', 'Suspicious Fraction'),
                    vertical_spacing=0.15
                )
                
                fig.add_trace(go.Scatter(x=health_df['Round'], y=health_df['Accuracy'],
                                       mode='lines+markers', name='Accuracy'), row=1, col=1)
                fig.add_trace(go.Scatter(x=health_df['Round'], y=health_df['Avg DPS'],
                                       mode='lines+markers', name='Avg DPS'), row=1, col=2)
                fig.add_trace(go.Scatter(x=health_df['Round'], y=health_df['Max DPS'],
                                       mode='lines+markers', name='Max DPS'), row=2, col=1)
                fig.add_trace(go.Scatter(x=health_df['Round'], y=health_df['Suspicious Fraction'],
                                       mode='lines+markers', name='Suspicious %'), row=2, col=2)
                
                fig.update_layout(height=600, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 6: Explanations
    with tab6:
        st.markdown("### 📚 Understanding ASH-FL")
        
        explanation_sections = get_explanation_content()
        
        for section_title, section_content in explanation_sections.items():
            with st.expander(f"**{section_title}**", expanded=(section_title == "🔍 What is DPS?")):
                st.markdown(section_content)

if __name__ == "__main__":
    main()
