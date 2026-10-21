"""
CAPS // ASH-FL Unified Research Dashboard
Adaptive Self-Healing Federated Learning (ASH-FL) Capstone Demonstration
Provides clean, minimal, research-grade evaluation and live simulation.
"""

import os
import sys
import time
import json
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure project root is available on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.simulator import DashboardSimulator
from dashboard.visualizations import (
    create_accuracy_chart,
    create_loss_chart,
    create_dps_radar,
    create_trust_evolution,
    create_aggregation_heatmap,
)
from defenses import (
    ComparisonRunner,
    ExperimentConfig,
    DefenseResult,
    ComparisonResult,
)
from dashboard.comparison_visualizations import (
    create_comparison_accuracy_bar,
    create_comparison_accuracy_trajectory,
    create_comparison_loss_trajectory,
    create_comparison_degradation_chart,
    create_comparison_backdoor_asr_chart,
    DEFENSE_COLORS,
)

# ==============================================================================
# Page Configuration
# ==============================================================================
st.set_page_config(
    page_title="ASH-FL // Federated Learning Defense Benchmark",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# Academic Restrained Dark Stylesheet
# Clean, minimal, high-contrast, presentation-ready layout
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-main: #0b0f19;
    --card-bg: #111827;
    --card-border: #1e293b;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-indigo: #6366f1;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --accent-sky: #0284c7;
}

/* Background & Core Layout */
.stApp {
    background-color: var(--bg-main) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-primary);
}

/* Clean Cards */
.clean-card {
    background-color: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}

/* Header Container */
.header-box {
    border-bottom: 1px solid #1e293b;
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
}

/* Academic Status Pills */
.pill {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    font-size: 0.75rem;
    font-weight: 500;
    border-radius: 9999px;
    background: #1e293b;
    color: var(--text-secondary);
    border: 1px solid #334155;
    margin-right: 0.4rem;
}

.pill-indigo {
    background: rgba(99, 102, 241, 0.12);
    color: #a5b4fc;
    border-color: rgba(99, 102, 241, 0.3);
}

.pill-emerald {
    background: rgba(16, 185, 129, 0.12);
    color: #6ee7b7;
    border-color: rgba(16, 185, 129, 0.3);
}

.pill-rose {
    background: rgba(244, 63, 94, 0.12);
    color: #fda4af;
    border-color: rgba(244, 63, 94, 0.3);
}

/* Metric Display Cards */
.metric-box {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    text-align: left;
}
.metric-box .metric-title {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
}
.metric-box .metric-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #f8fafc;
    font-family: 'JetBrains Mono', monospace;
}
.metric-box .metric-sub {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
}

/* Table Enhancements */
div[data-testid="stDataFrame"] {
    border: 1px solid #1e293b;
    border-radius: 8px;
    overflow: hidden;
}

/* Clean Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0d1322 !important;
    border-right: 1px solid #1e293b !important;
}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Header
# ==============================================================================
def render_header(current_attack_label: str = "Label Flip"):
    """Render academic demonstration header."""
    st.markdown(f"""
    <div class="header-box">
        <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="display: flex; gap: 6px; margin-bottom: 6px;">
                    <span class="pill pill-indigo">CAPSTONE RESEARCH</span>
                    <span class="pill pill-emerald">UCI HEART DISEASE (45)</span>
                    <span class="pill">5 CLIENTS &bull; 3 ROUNDS</span>
                </div>
                <h2 style="margin: 0; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.02em; color: #f8fafc;">
                    Adaptive Self-Healing Federated Learning (ASH-FL)
                </h2>
                <div style="color: #94a3b8; font-size: 0.92rem; margin-top: 4px;">
                    Adversarial Robustness Benchmark & Autonomous Checkpoint Recovery under Byzantine Attacks
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.78rem; color: #64748b; margin-bottom: 4px;">ACTIVE SCENARIO</div>
                <span class="pill pill-rose" style="font-size: 0.85rem; padding: 0.3rem 0.8rem; font-weight: 600;">
                    {current_attack_label.upper()}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# Defense Comparison Benchmark (Primary View)
# ==============================================================================
def render_defense_comparison():
    """Render the main Capstone Defense Comparison benchmark tab."""
    # ── 1. Functional Controls Card ──
    st.markdown('<div class="clean-card" style="padding: 1.25rem;">', unsafe_allow_html=True)
    c_atk, c_btn = st.columns([3, 1])

    with c_atk:
        attack_options = ["Label Flip", "Sign Flip", "Scaling", "Backdoor", "None (Clean FL)"]
        selected_attack_label = st.selectbox(
            "Threat Scenario / Adversarial Vector:",
            attack_options,
            index=0,
            key="benchmark_threat_select",
            help="Select the adversarial attack injected during federated training across malicious clients.",
        )

    attack_map = {
        "Label Flip": "label_flip",
        "Sign Flip": "sign_flip",
        "Scaling": "scaling",
        "Backdoor": "backdoor",
        "None (Clean FL)": "none",
    }
    atk_key = attack_map[selected_attack_label]

    st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #cbd5e1; margin: 0.75rem 0 0.4rem 0;'>Compare Defenses:</div>", unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        use_ash = st.checkbox("ASH-FL (Primary Defense)", value=True, disabled=True, key="chk_ash",
                              help="Mandatory proposed capstone defense. Multi-signal DPS, adaptive trust decay, quarantine, and autonomous checkpoint rollback.")
    with d2:
        use_mk = st.checkbox("Multi-Krum (Optional)", value=True, key="chk_mk",
                             help="Distance-based robust aggregation (Blanchard et al., NeurIPS 2017).")
    with d3:
        use_tm = st.checkbox("Trimmed Mean (Optional)", value=True, key="chk_tm",
                             help="Coordinate-wise parameter trimming with k=1 (Yin et al., ICML 2018).")
    with d4:
        use_flt = st.checkbox("FLTrust (Optional)", value=True, key="chk_flt",
                              help="Clean server root bootstrapping and cosine trust weighting (Cao et al., NDSS 2021).")

    selected_defense_names = ["ASH-FL"]
    if use_mk: selected_defense_names.append("Multi-Krum")
    if use_tm: selected_defense_names.append("Trimmed Mean")
    if use_flt: selected_defense_names.append("FLTrust")

    with c_btn:
        st.write("")
        st.write("")
        run_comp_btn = st.button("⚡ Run Evaluation", type="primary", use_container_width=True, key="btn_run_comp",
                                 help="Execute live comparison across selected defenses under strictly matched conditions.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. Data Loading & Execution Logic ──
    results_dir = os.path.join(PROJECT_ROOT, "results", "defense_comparison")
    json_path = os.path.join(results_dir, f"{atk_key}.json")

    if run_comp_btn:
        with st.spinner(f"Executing federated comparison matrix for {selected_attack_label}..."):
            config = ExperimentConfig(
                num_clients=5,
                num_rounds=3,
                local_epochs=3,
                batch_size=16,
                learning_rate=0.01,
                random_seed=42,
                scale_factor=50.0,
            )
            runner = ComparisonRunner(config)
            comp_res = runner.run_comparison(
                attack_type=atk_key,
                defense_names=selected_defense_names,
            )
            st.session_state.comparison_results = comp_res
            st.session_state.comparison_attack_label = selected_attack_label
            st.success(f"Evaluation completed for {selected_attack_label}.")
    else:
        # Load verified saved results from disk
        cached = st.session_state.get("comparison_results")
        cached_label = st.session_state.get("comparison_attack_label")

        if cached is None or cached_label != selected_attack_label:
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    d_results = {}
                    for d_name, d_dict in data["defense_results"].items():
                        d_results[d_name] = DefenseResult(**d_dict)
                    comp_res = ComparisonResult(
                        attack_type=data["attack_type"],
                        config=data["config"],
                        defense_results=d_results,
                    )
                    st.session_state.comparison_results = comp_res
                    st.session_state.comparison_attack_label = selected_attack_label
                except Exception as e:
                    st.error(f"Error loading saved results: {e}")

    comp_res: Optional[ComparisonResult] = st.session_state.get("comparison_results")
    if comp_res is None or not comp_res.defense_results:
        st.info("💡 Select an attack scenario above and click **⚡ Run Evaluation** to display the benchmark.")
        return

    # Filter active results by user checkboxes (ASH-FL is always included)
    active_defense_results = {
        name: res for name, res in comp_res.defense_results.items()
        if name in selected_defense_names
    }

    if not active_defense_results:
        st.warning("⚠️ No results available for the selected defenses. Click Run Evaluation to generate.")
        return

    # ── 3. Focused Results Summary Ribbon ──
    ash_res = active_defense_results.get("ASH-FL")
    if ash_res is not None:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">Initial Model Accuracy</div>
                <div class="metric-value">{ash_res.initial_accuracy:.1%}</div>
                <div class="metric-sub">Seed 42 initial weights (20/30 test)</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">ASH-FL Final Accuracy</div>
                <div class="metric-value" style="color: #a5b4fc;">{ash_res.final_accuracy:.1%}</div>
                <div class="metric-sub">Loss: {ash_res.final_loss:.4f} (Round 3)</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            deg_sign = f"{ash_res.accuracy_degradation:+.1%}"
            deg_color = "#10b981" if ash_res.accuracy_degradation <= 0 else "#f43f5e"
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">Accuracy Degradation</div>
                <div class="metric-value" style="color: {deg_color};">{deg_sign}</div>
                <div class="metric-sub">vs. Clean Baseline ({ash_res.clean_accuracy:.1%})</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            if atk_key == "backdoor":
                asr_val = f"{ash_res.backdoor_asr:.1%}" if ash_res.backdoor_asr is not None else "N/A"
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-title">Backdoor Attack ASR</div>
                    <div class="metric-value" style="color: #34d399;">{asr_val}</div>
                    <div class="metric-sub">Lower is Better (2/15 non-target samples)</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                fsm_st = ash_res.recovery_metrics.get("final_fsm_state", "NORMAL")
                rec_att = ash_res.recovery_metrics.get("recovery_attempts", 0)
                rec_text = f"Triggered ({rec_att} attempts)" if rec_att > 0 else f"Healthy ({fsm_st})"
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-title">Autonomous Recovery</div>
                    <div class="metric-value" style="font-size: 1.25rem; padding-top: 0.35rem;">{rec_text}</div>
                    <div class="metric-sub">FSM State: {fsm_st}</div>
                </div>
                """, unsafe_allow_html=True)

    st.write("")

    # ── 4. Main Results Table ──
    st.markdown("#### 📋 Defense Comparison Summary Table")
    table_rows = []
    for name, res in active_defense_results.items():
        row = {
            "Defense Strategy": name,
            "Type": res.defense_type.replace("_", " ").title(),
            "Initial Acc": f"{res.initial_accuracy:.1%}",
            "Final Acc": f"{res.final_accuracy:.1%}",
            "Clean Baseline": f"{res.clean_accuracy:.1%}",
            "Acc Degradation": f"{res.accuracy_degradation:+.1%}",
            "Final Loss": f"{res.final_loss:.4f}",
            "Backdoor ASR": f"{res.backdoor_asr:.1%}" if (atk_key == "backdoor" and res.backdoor_asr is not None) else "—",
            "Self-Healing Supported": "YES (Autonomous FSM)" if res.supports_self_healing else "N/A",
        }
        if res.supports_self_healing:
            attempts = res.recovery_metrics.get("recovery_attempts", 0)
            state = res.recovery_metrics.get("final_fsm_state", "NORMAL")
            row["Recovery Status"] = f"Attempts: {attempts} | State: {state}"
        else:
            row["Recovery Status"] = "N/A (Robust Agg)"
        table_rows.append(row)

    df_table = pd.DataFrame(table_rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.write("")

    # ── 5. Focused Visualizations (Only 2 Core Charts) ──
    st.markdown("#### 📊 Performance Visualizations")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_bar = create_comparison_accuracy_bar(active_defense_results)
        st.plotly_chart(fig_bar, use_container_width=True, key="main_acc_bar")

    with col_chart2:
        fig_traj = create_comparison_accuracy_trajectory(active_defense_results)
        st.plotly_chart(fig_traj, use_container_width=True, key="main_acc_traj")

    # Backdoor ASR chart rendered strictly when backdoor experiment is selected
    if atk_key == "backdoor":
        st.write("")
        fig_asr = create_comparison_backdoor_asr_chart(active_defense_results)
        if fig_asr is not None:
            st.plotly_chart(fig_asr, use_container_width=True, key="main_backdoor_asr")
            st.caption(
                "**Attack Success Rate (ASR):** Evaluated strictly on non-target clean test samples (label 0) stamped with the trojan trigger pattern. "
                "Lower ASR indicates superior resilience against backdoor trojan injection."
            )

    st.write("")

    # ── 6. Secondary Collapsible Technical Diagnostics ──
    with st.expander("🔬 Technical Diagnostics & Defense Telemetry", expanded=False):
        st.markdown("""
        <div style="font-size: 0.88rem; color: #94a3b8; margin-bottom: 0.75rem;">
            Inspect low-level algorithm telemetry: Multi-Krum pairwise distance scores, Trimmed Mean trimming bounds, 
            FLTrust root gradient norms, and ASH-FL multi-signal Dynamic Protection Scores (DPS).
        </div>
        """, unsafe_allow_html=True)

        # ASH-FL Telemetry
        if "ASH-FL" in active_defense_results:
            ash_res = active_defense_results["ASH-FL"]
            last_m = ash_res.per_round_defense_metrics[-1] if ash_res.per_round_defense_metrics else {}
            st.markdown("**🟣 Proposed ASH-FL Telemetry (Final Round):**")
            diag_cols = st.columns(4)
            if "G_scores" in last_m and last_m["G_scores"]:
                with diag_cols[0]: st.metric("Max G (Gradient)", f"{max(last_m['G_scores'].values()):.3f}")
            if "C_scores" in last_m and last_m["C_scores"]:
                with diag_cols[1]: st.metric("Max C (Cosine)", f"{max(last_m['C_scores'].values()):.3f}")
            if "H_scores" in last_m and last_m["H_scores"]:
                with diag_cols[2]: st.metric("Max H (History)", f"{max(last_m['H_scores'].values()):.3f}")
            if "P_scores" in last_m and last_m["P_scores"]:
                with diag_cols[3]: st.metric("Max P (Shadow Val)", f"{max(last_m['P_scores'].values()):.3f}")

            if "dps_scores" in last_m:
                st.markdown(r"*Normalized DPS Scores ($DPS_i \in [0, 1]$):*")
                st.json(last_m["dps_scores"])

        # Baseline Diagnostics
        if "Multi-Krum" in active_defense_results:
            mk_res = active_defense_results["Multi-Krum"]
            last_m = mk_res.per_round_defense_metrics[-1] if mk_res.per_round_defense_metrics else {}
            st.markdown(f"""
            **🔷 Multi-Krum Telemetry (f=1, m=4):**  
            - Selected Client IDs: `{last_m.get('selected_clients', [])}`  
            - Excluded Outlier Client IDs: `{last_m.get('excluded_clients', [])}`
            """)

        if "Trimmed Mean" in active_defense_results:
            tm_res = active_defense_results["Trimmed Mean"]
            last_m = tm_res.per_round_defense_metrics[-1] if tm_res.per_round_defense_metrics else {}
            st.markdown(f"""
            **🔶 Trimmed Mean Telemetry (k=1):**  
            - Trimming: Discards {last_m.get('trim_k', 1)} minimum and {last_m.get('trim_k', 1)} maximum per coordinate.  
            - Retained Coordinates per Parameter: {last_m.get('retained_per_coordinate', 3)} / {last_m.get('num_clients', 5)}
            """)

        if "FLTrust" in active_defense_results:
            flt_res = active_defense_results["FLTrust"]
            last_m = flt_res.per_round_defense_metrics[-1] if flt_res.per_round_defense_metrics else {}
            st.markdown(r"""
            **🟢 FLTrust Telemetry (Server Root Data N=30):**  
            - Server Root Update Norm $\|g_0\|$: """ + f"`{last_m.get('server_update_norm', 0.0):.4f}`  \n            - Trust Scores:\n            ")
            if "trust_scores" in last_m:
                st.json(last_m["trust_scores"])


# ==============================================================================
# Secondary View: Interactive Simulation (Preserved Simulator)
# ==============================================================================
def render_interactive_simulation(num_clients: int, dps_threshold: float):
    """Render the preserved live single-simulation tab."""
    st.markdown("""
    <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 1rem;">
        Execute an interactive step-by-step federated training simulation with custom client attack injections, 
        live multi-signal telemetry (G/C/H/P/D), and autonomous FSM self-healing.
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.get("simulation_run", False):
        st.info("💡 Configure parameters in the sidebar and click **Execute Simulation** to run a live federated learning session.")
    else:
        results = st.session_state.simulation_results

        # Sub-tabs for simulator
        sim_tab1, sim_tab2, sim_tab3 = st.tabs(["Overview & Metrics", "DPS Radar & Telemetry", "Self-Healing FSM Log"])

        with sim_tab1:
            st.markdown("##### Global Model Convergence")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                fig_acc = create_accuracy_chart(results)
                st.plotly_chart(fig_acc, use_container_width=True)
            with col_s2:
                fig_loss = create_loss_chart(results)
                st.plotly_chart(fig_loss, use_container_width=True)

            st.markdown("##### Trust Evolution & Weight Allocation")
            fig_trust = create_trust_evolution(results)
            st.plotly_chart(fig_trust, use_container_width=True)

        with sim_tab2:
            st.markdown("##### Multi-Signal Radar Breakdown (G, C, H, P, D)")
            client_id = st.selectbox("Select Client for Radar Analysis:", list(range(num_clients)), index=0)
            fig_radar = create_dps_radar(results, client_id)
            st.plotly_chart(fig_radar, use_container_width=True)

        with sim_tab3:
            st.markdown("##### Autonomous Self-Healing FSM Status")
            st.write(f"**Recovery Attempts:** {results.get('recovery_attempts', 0)}")
            st.write(f"**Total Checkpoints Retained:** {results.get('total_checkpoints', 0)}")
            st.write(f"**Quarantined Clients:** {results.get('quarantined_clients', [])}")

            # Round by round timeline
            if "rounds" in results:
                history = [
                    {
                        "Round": r["round"],
                        "FSM State": r["state"],
                        "Accuracy": f"{r['metrics']['accuracy']:.1%}",
                        "Loss": f"{r['metrics']['loss']:.4f}",
                        "Quarantined": r.get("quarantined", []),
                    }
                    for r in results["rounds"]
                ]
                st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)


# ==============================================================================
# Sidebar Simulation Controls
# ==============================================================================
def render_sidebar():
    """Render sidebar simulation controller."""
    with st.sidebar:
        st.markdown("### ⚙️ Live Simulator Settings")
        st.caption("Optional step-by-step federated training simulation.")

        num_clients = st.slider("Total Clients (K)", 3, 10, 5)
        num_rounds = st.slider("Federation Rounds", 3, 15, 5)
        random_seed = st.number_input("Random Seed", 0, 9999, 42)

        st.markdown("---")
        st.markdown("**Adversarial Configuration**")
        enable_attack = st.checkbox("Enable Client Attacks", value=True)
        client_attacks = {}
        scale_factor = 50.0

        if enable_attack:
            preset = st.selectbox("Attack Preset:", ["2 Scaling", "2 Label-Flip", "Mixed Attacks", "Custom"])
            if preset == "2 Scaling":
                for i in range(num_clients): client_attacks[i] = "scaling" if i < 2 else "none"
            elif preset == "2 Label-Flip":
                for i in range(num_clients): client_attacks[i] = "label_flip" if i < 2 else "none"
            elif preset == "Mixed Attacks":
                attacks = ["scaling", "label_flip", "sign_flip", "none", "none"]
                for i in range(num_clients): client_attacks[i] = attacks[i] if i < len(attacks) else "none"
            else:
                for i in range(num_clients):
                    client_attacks[i] = st.selectbox(f"Client {i}:", ["none", "scaling", "label_flip", "sign_flip", "backdoor"], key=f"atk_sel_{i}")
            scale_factor = st.slider("Scaling Factor", 1.0, 100.0, 50.0, 5.0)
        else:
            for i in range(num_clients): client_attacks[i] = "none"

        st.markdown("---")
        st.markdown("**Autonomous Self-Healing**")
        enable_self_healing = st.checkbox("Enable Self-Healing FSM", value=True)
        dps_threshold = 0.55
        recovery_rounds = 3
        if enable_self_healing:
            dps_threshold = st.slider("DPS Alert Threshold", 0.3, 1.0, 0.55, 0.05)
            recovery_rounds = st.slider("Recovery Window (Rounds)", 1, 5, 3)

        st.markdown("---")
        c_run, c_rst = st.columns(2)
        with c_run:
            run_clicked = st.button("Execute Sim", type="primary", use_container_width=True)
        with c_rst:
            reset_clicked = st.button("Reset", use_container_width=True)

        if run_clicked:
            with st.spinner("Executing live simulation..."):
                sim_config = {
                    "num_clients": num_clients,
                    "num_rounds": num_rounds,
                    "random_seed": random_seed,
                    "enable_attack": enable_attack,
                    "client_attacks": client_attacks,
                    "scale_factor": scale_factor,
                    "enable_self_healing": enable_self_healing,
                    "dps_threshold": dps_threshold,
                    "recovery_rounds": recovery_rounds,
                }
                simulator = DashboardSimulator(sim_config)
                results = simulator.run_full_simulation()
                st.session_state.simulation_run = True
                st.session_state.simulation_results = results
                st.rerun()

        if reset_clicked:
            st.session_state.simulation_run = False
            st.session_state.simulation_results = None
            st.rerun()

        return num_clients, dps_threshold


# ==============================================================================
# Main Entry Point
# ==============================================================================
def main():
    """Main dashboard application entry point."""
    if "simulation_run" not in st.session_state:
        st.session_state.simulation_run = False
    if "simulation_results" not in st.session_state:
        st.session_state.simulation_results = None

    num_clients, dps_threshold = render_sidebar()

    current_attack = st.session_state.get("comparison_attack_label", "Label Flip")
    render_header(current_attack)

    # Primary tabs: Defense Benchmark (Default) & Interactive Simulation
    tab_benchmark, tab_simulation = st.tabs([
        "📊 Defense Benchmark",
        "🧪 Interactive Simulation",
    ])

    with tab_benchmark:
        render_defense_comparison()

    with tab_simulation:
        render_interactive_simulation(num_clients, dps_threshold)


if __name__ == "__main__":
    main()
