"""
CAPS // ASH-FL Unified Research Dashboard
Adaptive Self-Healing Federated Learning (ASH-FL) Capstone Demonstration
Provides clean, minimal, research-grade evaluation and live simulation.
"""

import os
import sys
import yaml
from datetime import datetime
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

with open(os.path.join(PROJECT_ROOT, "configs", "sim_config.yaml"), encoding="utf-8") as _f:
    PROJECT_CONFIG = yaml.safe_load(_f)

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
    ComparisonResult,
)
from recovery.health_monitor import HealthMonitor
from dashboard.comparison_visualizations import (
    create_comparison_accuracy_bar,
    create_comparison_accuracy_trajectory,
    create_comparison_loss_trajectory,
    create_comparison_degradation_chart,
    create_comparison_backdoor_asr_chart,
    create_attack_defense_accuracy_heatmap,
    create_client_trust_timeline,
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

/* Editorial lab interface, inspired by the reference site's oversized type,
   quiet grid, and vivid accent color. */
:root {
    --bg-main: #10120f;
    --card-bg: #171a15;
    --card-border: #30352b;
    --text-primary: #f0f0e9;
    --text-secondary: #a9afa0;
    --text-muted: #777e70;
    --accent-indigo: #c7f36b;
    --accent-emerald: #c7f36b;
}

.stApp {
    background:
      radial-gradient(ellipse at 82% 2%, rgba(199,243,107,.075), transparent 28rem),
      linear-gradient(180deg, #10120f 0%, #121510 46%, #10120f 100%) !important;
}

section[data-testid="stSidebar"] { background: #141711 !important; border-color: #30352b !important; }
div[data-testid="stAppViewContainer"] > .main .block-container {
    max-width: 1500px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
}

.header-box {
    position: relative;
    overflow: hidden;
    min-height: 255px;
    display: flex;
    align-items: center;
    padding: 2.1rem 2.3rem;
    margin-bottom: 1.8rem;
    border: 1px solid #34392e;
    border-radius: 18px;
    background:
      radial-gradient(circle at 83% 48%, rgba(199,243,107,.12), transparent 15rem),
      linear-gradient(115deg, #171a15 0%, #141711 62%, #1b2016 100%);
}
.header-box::after {
    content: "";
    position: absolute;
    width: 235px;
    height: 235px;
    right: 8%;
    top: 50%;
    transform: translateY(-50%);
    border: 1px solid rgba(199,243,107,.42);
    border-radius: 50%;
    box-shadow: 0 0 0 24px rgba(199,243,107,.035), 0 0 0 54px rgba(199,243,107,.025), inset 0 0 50px rgba(199,243,107,.08);
    pointer-events: none;
}
.header-box > div { position: relative; z-index: 1; width: 100%; }
.header-box h2 {
    max-width: 820px;
    font-size: clamp(2rem, 4.3vw, 3.55rem) !important;
    line-height: .99 !important;
    letter-spacing: -.065em !important;
    text-transform: uppercase;
    font-weight: 700 !important;
    margin-top: 1rem !important;
}
.header-box > div > div:first-child { gap: 8px !important; }
.pill {
    border-radius: 4px;
    letter-spacing: .1em;
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
}
.pill-indigo { color: #d4ff86; background: rgba(199,243,107,.09); border-color: rgba(199,243,107,.28); }
.pill-emerald { color: #c6ccc0; background: rgba(255,255,255,.035); border-color: #444a3e; }
.pill-rose { color: #d4ff86; background: rgba(199,243,107,.09); border-color: rgba(199,243,107,.3); }

.clean-card, .metric-box {
    background: linear-gradient(145deg, #1a1d17, #151812);
    border: 1px solid #30352b;
    border-radius: 12px;
    box-shadow: 0 12px 36px rgba(0,0,0,.12);
}
.metric-box { min-height: 132px; padding: 1.2rem 1.3rem; }
.metric-box .metric-title { font-family: 'JetBrains Mono', monospace; font-size: .67rem; letter-spacing: .095em; color: #a2aa96; }
.metric-box .metric-value { font-size: 2rem; letter-spacing: -.06em; }
.metric-box .metric-sub { color: #858d7d; }

h1, h2, h3, h4 { letter-spacing: -.045em; }
h3 { font-size: 1.35rem !important; }
[data-testid="stMarkdownContainer"] h4 { margin-top: 2rem; color: #e9eddf; }
div[data-testid="stDataFrame"], div[data-testid="stTable"] { border: 1px solid #30352b; border-radius: 10px; }
div[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid #34392e; gap: .4rem; }
div[data-testid="stTabs"] button[role="tab"] { color: #9aa18f; padding: .8rem 1rem; }
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: #d4ff86; border-bottom-color: #c7f36b; }
div[data-testid="stExpander"] { border: 1px solid #30352b; border-radius: 10px; background: rgba(23,26,21,.65); }
div[data-testid="stNumberInput"] input, div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div { background-color: #11140f; border-color: #3a4033; }
div[data-testid="stCheckbox"] label, div[data-testid="stWidgetLabel"] p { color: #c3c9b9; }
div.stButton > button, div[data-testid="stDownloadButton"] button {
    border-radius: 6px;
    border: 1px solid #454d39;
    background: #20251b;
    color: #edf2e4;
    transition: transform .18s ease, border-color .18s ease, background .18s ease;
}
div.stButton > button:hover, div[data-testid="stDownloadButton"] button:hover {
    border-color: #c7f36b;
    background: #292f20;
    color: #e3ffad;
    transform: translateY(-1px);
}
div.stButton > button[kind="primary"] { background: #c7f36b; color: #171a12; border-color: #c7f36b; font-weight: 700; }
div.stButton > button[kind="primary"]:hover { background: #d6ff87; color: #11140d; }
@media (max-width: 760px) {
    .header-box { min-height: 210px; padding: 1.4rem; }
    .header-box::after { width: 135px; height: 135px; right: -2rem; opacity: .6; }
    .header-box h2 { max-width: 90%; font-size: 2rem !important; }
}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Header
# ==============================================================================
def render_header(current_attack_label: str = "Label Flip"):
    """Render the ASH-FL research lab hero header."""
    st.markdown(f"""
    <div class="header-box">
        <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="display: flex; gap: 6px; margin-bottom: 6px;">
                    <span class="pill pill-indigo">FEDERATED SECURITY LAB / 01</span>
                    <span class="pill pill-emerald">UCI HEART DISEASE · LOCAL DATA</span>
                </div>
                <h2 style="margin: 0; color: #f0f0e9;">
                    Train together.<br>Defend together.
                </h2>
                <div style="color: #a9afa0; font-size: 0.95rem; margin-top: 1rem; max-width: 620px; line-height: 1.6;">
                    ASH-FL · Adversarial robustness benchmarking and autonomous recovery across federated clients.
                </div>
            </div>
            <div style="text-align: right; margin-left: auto; align-self: flex-end;">
                <div style="font-size: 0.66rem; color: #9ba38e; letter-spacing: .13em; font-family: 'JetBrains Mono', monospace; margin-bottom: 8px;">LATEST EXPERIMENT</div>
                <span class="pill pill-rose" style="font-size: 0.72rem; padding: 0.45rem 0.75rem; font-weight: 600;">
                    {current_attack_label.upper()} ↗
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def build_client_detection_report(
    results_by_attack: Dict[str, ComparisonResult],
    num_clients: int,
    injected_malicious_ids: List[int],
    dps_threshold: float,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize ASH-FL anomaly alerts and actual quarantine actions by client.

    Injected attacker IDs are used only for benchmark scoring; detector flags and
    quarantine actions come exclusively from ASH-FL DPS/FSM output.
    """
    attack_labels = {
        "label_flip": "Label Flip",
        "sign_flip": "Sign Flip",
        "scaling": "Scaling",
        "backdoor": "Backdoor",
        "none": "Clean",
    }
    malicious_ids = {int(cid) for cid in injected_malicious_ids}
    detail_rows = []
    metric_rows = []
    detector = HealthMonitor(dps_threshold=dps_threshold)

    for attack_key, comparison in results_by_attack.items():
        ash_result = comparison.defense_results.get("ASH-FL")
        if ash_result is None:
            continue

        per_client_dps = {cid: [] for cid in range(num_clients)}
        per_client_quarantines = {cid: [] for cid in range(num_clients)}
        per_client_weights = {cid: [] for cid in range(num_clients)}
        for round_index, round_metrics in enumerate(ash_result.per_round_defense_metrics, start=1):
            for cid, score in round_metrics.get("dps_scores", {}).items():
                if int(cid) in per_client_dps:
                    per_client_dps[int(cid)].append((round_index, float(score)))
            for cid in round_metrics.get("quarantined_clients", []):
                if int(cid) in per_client_quarantines:
                    per_client_quarantines[int(cid)].append(round_index)
            for cid, weight in round_metrics.get("aggregation_weights", {}).items():
                if int(cid) in per_client_weights:
                    per_client_weights[int(cid)].append(float(weight))

        attack_name = attack_labels.get(attack_key, attack_key.replace("_", " ").title())
        quarantined_ids = {
            cid for cid, rounds in per_client_quarantines.items() if rounds
        }
        true_positives = quarantined_ids & malicious_ids
        precision = len(true_positives) / len(quarantined_ids) if quarantined_ids else None
        recall = len(true_positives) / len(malicious_ids) if malicious_ids else None
        metric_rows.append({
            "Attack": attack_name,
            "Injected attackers": len(malicious_ids),
            "Clients quarantined": len(quarantined_ids),
            "Quarantine precision (%)": precision * 100 if precision is not None else None,
            "Quarantine recall (%)": recall * 100 if recall is not None else None,
        })

        for cid in range(num_clients):
            scored_rounds = per_client_dps[cid]
            flagged_rounds = [
                round_num
                for round_num, score in scored_rounds
                if cid in detector.get_dps_outliers(
                    {
                        other_cid: other_score
                        for other_cid in range(num_clients)
                        for other_round, other_score in per_client_dps[other_cid]
                        if other_round == round_num
                    }
                )
            ]
            quarantine_rounds = per_client_quarantines[cid]
            if quarantine_rounds:
                action = "Quarantined and down-weighted"
            elif flagged_rounds:
                action = "DPS alert; adaptive weighting applied"
            else:
                action = "No DPS alert; normal adaptive weighting"
            detail_rows.append({
                "Attack": attack_name,
                "Client": cid,
                "Injected attacker (scoring only)": cid in malicious_ids,
                "DPS alert rounds": ", ".join(map(str, flagged_rounds)) or "—",
                "Peak DPS": max((score for _, score in scored_rounds), default=0.0),
                "Quarantine rounds": ", ".join(map(str, quarantine_rounds)) or "—",
                "Mean aggregation weight (%)": (
                    100 * float(np.mean(per_client_weights[cid]))
                    if per_client_weights[cid] else 0.0
                ),
                "Action": action,
            })

    return pd.DataFrame(detail_rows), pd.DataFrame(metric_rows)


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

    c_clients, c_rounds, c_epochs, c_seed = st.columns(4)
    with c_clients:
        benchmark_clients = st.number_input("Clients", min_value=3, max_value=20,
                                            value=int(PROJECT_CONFIG["num_clients_total"]))
    with c_rounds:
        benchmark_rounds = st.number_input("Rounds", min_value=1, max_value=100,
                                           value=int(PROJECT_CONFIG["num_rounds"]))
    with c_epochs:
        benchmark_epochs = st.number_input("Local epochs", min_value=1, max_value=50,
                                           value=int(PROJECT_CONFIG["local_epochs"]))
    with c_seed:
        benchmark_seed = st.number_input("Random seed", min_value=0, max_value=999999,
                                         value=int(PROJECT_CONFIG["random_seed"]))
    benchmark_malicious_ids = st.multiselect(
        "Malicious client IDs",
        options=list(range(int(benchmark_clients))),
        default=[
            int(cid) for cid in PROJECT_CONFIG["attack"]["malicious_client_ids"]
            if int(cid) < int(benchmark_clients)
        ],
        help="These client IDs receive the selected attack. The clean scenario ignores this selection.",
    )
    project_config_signature = (
        PROJECT_CONFIG["dataset_path"], float(PROJECT_CONFIG["test_split"]),
        bool(PROJECT_CONFIG["iid"]), int(PROJECT_CONFIG["batch_size"]),
        float(PROJECT_CONFIG["learning_rate"]), PROJECT_CONFIG["optimizer_type"],
        int(PROJECT_CONFIG["hidden_dim"]),
        tuple(PROJECT_CONFIG["attack"]["trigger_feature_indices"]),
        int(PROJECT_CONFIG["attack"]["source_label"]),
        int(PROJECT_CONFIG["attack"]["target_label"]),
        float(PROJECT_CONFIG["attack"]["scale_factor"]),
        float(PROJECT_CONFIG["attack"]["trigger_value"]),
        float(PROJECT_CONFIG["attack"]["poison_fraction"]),
        int(PROJECT_CONFIG["attack"]["backdoor_target_label"]),
        float(PROJECT_CONFIG["self_healing"]["dps_threshold"]),
        int(PROJECT_CONFIG["self_healing"]["recovery_rounds"]),
    )
    matrix_signature = (
        "all_attacks_all_defenses", int(benchmark_clients), int(benchmark_rounds),
        int(benchmark_epochs), int(benchmark_seed), tuple(benchmark_malicious_ids),
        project_config_signature,
    )

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
                                 disabled=(atk_key != "none" and not benchmark_malicious_ids),
                                 help="Choose at least one malicious client for an attack scenario. Runs a fresh comparison.")

    run_matrix_btn = st.button(
        "🧮 Run All Attacks × All Defenses",
        use_container_width=True,
        key="btn_run_attack_defense_matrix",
        disabled=not benchmark_malicious_ids,
        help="Runs label-flip, sign-flip, scaling, and backdoor against ASH-FL, Multi-Krum, Trimmed Mean, and FLTrust with the same selected malicious clients and experiment settings.",
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Results are shown only after this page executes a fresh simulation.
    if run_comp_btn or run_matrix_btn:
        config = ExperimentConfig(
            num_clients=int(benchmark_clients),
            num_rounds=int(benchmark_rounds),
            local_epochs=int(benchmark_epochs),
            batch_size=int(PROJECT_CONFIG["batch_size"]),
            learning_rate=float(PROJECT_CONFIG["learning_rate"]),
            optimizer_type=PROJECT_CONFIG["optimizer_type"],
            random_seed=int(benchmark_seed),
            malicious_client_ids=list(benchmark_malicious_ids),
            dataset_path=os.path.join(PROJECT_ROOT, PROJECT_CONFIG["dataset_path"]),
            test_split=float(PROJECT_CONFIG["test_split"]),
            iid=bool(PROJECT_CONFIG["iid"]),
            hidden_dim=int(PROJECT_CONFIG["hidden_dim"]),
            scale_factor=float(PROJECT_CONFIG["attack"]["scale_factor"]),
            source_label=int(PROJECT_CONFIG["attack"]["source_label"]),
            target_label=int(PROJECT_CONFIG["attack"]["target_label"]),
            trigger_feature_indices=list(PROJECT_CONFIG["attack"]["trigger_feature_indices"]),
            trigger_value=float(PROJECT_CONFIG["attack"]["trigger_value"]),
            poison_fraction=float(PROJECT_CONFIG["attack"]["poison_fraction"]),
            backdoor_target_label=int(PROJECT_CONFIG["attack"]["backdoor_target_label"]),
            dps_threshold=float(PROJECT_CONFIG["self_healing"]["dps_threshold"]),
            recovery_rounds=int(PROJECT_CONFIG["self_healing"]["recovery_rounds"]),
        )
        runner = ComparisonRunner(config)
        eval_labels = runner.eval_test_data[1]
        st.session_state.comparison_data_summary = {
            "evaluation_samples": int(len(eval_labels)),
            "non_target_samples": int(np.count_nonzero(eval_labels != config.backdoor_target_label)),
            "dataset_path": config.dataset_path,
        }

        if run_matrix_btn:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            matrix_output_dir = os.path.join(
                PROJECT_ROOT, "results", "attack_defense_matrix", f"run_{run_id}"
            )
            attacks = ["label_flip", "sign_flip", "scaling", "backdoor"]
            progress = st.progress(0.0)
            progress_label = st.empty()

            def update_matrix_progress(attack: str, message: str) -> None:
                current = attacks.index(attack)
                progress.progress(current / len(attacks))
                progress_label.write(
                    f"Running attack {current + 1}/{len(attacks)}: {attack.replace('_', ' ').title()}"
                )

            with st.spinner("Running 4 attacks across all 4 defense strategies. This may take several minutes..."):
                matrix_results = runner.run_full_matrix(
                    output_dir=matrix_output_dir,
                    progress_callback=update_matrix_progress,
                )
            progress.progress(1.0)
            progress_label.write("All 16 attack-defense runs completed.")
            st.session_state.comparison_matrix_results = matrix_results
            st.session_state.comparison_matrix_signature = matrix_signature
            st.session_state.comparison_matrix_output_dir = matrix_output_dir
            st.session_state.comparison_signature = None
            st.session_state.comparison_attack_label = "All Attacks"
            st.success(f"Matrix completed. Run files saved to {matrix_output_dir}.")
        else:
            comp_res = runner.run_comparison(
                attack_type=atk_key,
                defense_names=selected_defense_names,
            )
            st.session_state.comparison_results = comp_res
            st.session_state.comparison_attack_label = selected_attack_label
            st.session_state.comparison_signature = (
                atk_key, tuple(selected_defense_names), int(benchmark_clients),
                int(benchmark_rounds), int(benchmark_epochs), int(benchmark_seed),
                tuple(benchmark_malicious_ids), project_config_signature,
            )
            st.session_state.comparison_matrix_signature = None
            st.success(f"Evaluation completed for {selected_attack_label}.")

    stored_matrix = st.session_state.get("comparison_matrix_results")
    if (
        st.session_state.get("comparison_matrix_signature") == matrix_signature
        and stored_matrix
    ):
        matrix_attack_labels = {
            "label_flip": "Label Flip",
            "sign_flip": "Sign Flip",
            "scaling": "Scaling",
            "backdoor": "Backdoor",
        }
        matrix_rows = []
        for attack_key, matrix_result in stored_matrix.items():
            for defense_name, result in matrix_result.defense_results.items():
                matrix_rows.append({
                    "Attack": matrix_attack_labels.get(attack_key, attack_key),
                    "Defense": defense_name,
                    "Final Accuracy (%)": result.final_accuracy * 100,
                    "Clean Baseline (%)": result.clean_accuracy * 100,
                    "Accuracy Degradation (pp)": result.accuracy_degradation * 100,
                    "Final Loss": result.final_loss,
                    "Backdoor ASR (%)": result.backdoor_asr * 100 if result.backdoor_asr is not None else None,
                    "Recovery Attempts": result.recovery_metrics.get("recovery_attempts", 0),
                    "Final FSM State": result.recovery_metrics.get("final_fsm_state", "N/A"),
                })
        matrix_df = pd.DataFrame(matrix_rows)
        st.markdown("#### All Attack × Defense Results")
        st.caption(
            f"Four attacks × four defenses, using seed {int(benchmark_seed)}, "
            f"{int(benchmark_clients)} clients, and {int(benchmark_rounds)} rounds. "
            f"Evaluation set: {st.session_state.comparison_data_summary['evaluation_samples']} records. "
            "All attack runs use the selected malicious client IDs and the same dataset split/configuration."
        )
        st.plotly_chart(
            create_attack_defense_accuracy_heatmap(stored_matrix),
            use_container_width=True,
            key="all_attack_defense_accuracy_heatmap",
        )
        st.dataframe(matrix_df, use_container_width=True, hide_index=True)
        detection_details, detection_metrics = build_client_detection_report(
            stored_matrix,
            int(benchmark_clients),
            list(benchmark_malicious_ids),
            float(PROJECT_CONFIG["self_healing"]["dps_threshold"]),
        )
        st.markdown("#### ASH-FL Client Detection & Response")
        st.caption(
            "DPS alerts are anomaly signals, not proof that a client is malicious. "
            "Quarantine precision/recall are scored against the injected client IDs, "
            "which are benchmark ground truth and are never fed into the detector. "
            "ASH-FL also adjusts aggregation weights using DPS each round."
        )
        st.dataframe(detection_metrics, use_container_width=True, hide_index=True)
        st.dataframe(detection_details, use_container_width=True, hide_index=True)
        matrix_graph_label = st.selectbox(
            "Trust timeline attack",
            options=list(stored_matrix.keys()),
            format_func=lambda key: matrix_attack_labels.get(key, key.replace("_", " ").title()),
            key="matrix_detection_timeline_attack",
        )
        graph_result = stored_matrix[matrix_graph_label].defense_results.get("ASH-FL")
        if graph_result is not None:
            st.plotly_chart(
                create_client_trust_timeline(
                    graph_result.per_round_defense_metrics,
                    int(benchmark_clients),
                    title=f"{matrix_attack_labels.get(matrix_graph_label, matrix_graph_label)} · Client Trust Scores",
                ),
                use_container_width=True,
                key="matrix_client_detection_timeline",
            )
            st.caption("Colored lines show each client's recorded trust score by round. Amber diamonds mark rounds when the client was quarantined. Lower trust contributes to a lower aggregation weight.")
        st.download_button(
            "Download attack-defense matrix CSV",
            data=matrix_df.to_csv(index=False),
            file_name=f"attack_defense_matrix_seed_{int(benchmark_seed)}.csv",
            mime="text/csv",
            key="download_attack_defense_matrix",
        )
        st.caption(f"JSON and summary CSV are also saved under `{st.session_state.comparison_matrix_output_dir}`.")
        return

    comp_res: Optional[ComparisonResult] = st.session_state.get("comparison_results")
    active_signature = (
        atk_key, tuple(selected_defense_names), int(benchmark_clients),
        int(benchmark_rounds), int(benchmark_epochs), int(benchmark_seed),
        tuple(benchmark_malicious_ids), project_config_signature,
    )
    if st.session_state.get("comparison_signature") != active_signature:
        comp_res = None
    if comp_res is None or not comp_res.defense_results:
        st.info("💡 Click **⚡ Run Evaluation** for one scenario or **🧮 Run All Attacks × All Defenses** for the complete matrix.")
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
                <div class="metric-sub">Seed {comp_res.config['random_seed']} · {st.session_state.comparison_data_summary['evaluation_samples']} evaluation records</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-title">ASH-FL Final Accuracy</div>
                <div class="metric-value" style="color: #a5b4fc;">{ash_res.final_accuracy:.1%}</div>
                <div class="metric-sub">Loss: {ash_res.final_loss:.4f} (Round {comp_res.config['num_rounds']})</div>
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
                    <div class="metric-sub">Lower is better · {st.session_state.comparison_data_summary['non_target_samples']} non-target evaluation records</div>
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

    if "ASH-FL" in active_defense_results:
        with st.expander("🕵️ ASH-FL Client Detection & Response", expanded=True):
            injected_ids = list(benchmark_malicious_ids) if atk_key != "none" else []
            detection_details, detection_metrics = build_client_detection_report(
                {atk_key: comp_res},
                int(benchmark_clients),
                injected_ids,
                float(PROJECT_CONFIG["self_healing"]["dps_threshold"]),
            )
            st.caption(
                "A DPS threshold crossing is a suspicion signal, not a confirmed malicious label. "
                "Quarantine metrics compare ASH-FL's actual quarantine decisions with injected IDs "
                "for this simulated run; those IDs do not affect detection."
            )
            st.dataframe(detection_metrics, use_container_width=True, hide_index=True)
            ash_detection_result = active_defense_results.get("ASH-FL")
            if ash_detection_result is not None:
                st.plotly_chart(
                    create_client_trust_timeline(
                        ash_detection_result.per_round_defense_metrics,
                        int(benchmark_clients),
                        title=f"{selected_attack_label} · Client Trust Scores",
                    ),
                    use_container_width=True,
                    key="single_client_detection_timeline",
                )
                st.caption("Colored lines show each client's recorded trust score by round. Amber diamonds mark rounds when the client was quarantined. Lower trust contributes to a lower aggregation weight.")
            st.dataframe(detection_details, use_container_width=True, hide_index=True)

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
            **🟢 FLTrust Telemetry (Server Root Data):**
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
        data_info = results.get("data", {})
        st.caption(
            f"Local data: {data_info.get('source_file', 'unknown')} · "
            f"{data_info.get('train_samples', '—')} train / "
            f"{data_info.get('test_samples', '—')} evaluation records "
            f"({data_info.get('validation_samples', '—')} validation) · "
            f"{data_info.get('input_features', '—')} features"
        )

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

        num_clients = st.slider(
            "Total Clients (K)", 3, 20, int(PROJECT_CONFIG["num_clients_total"])
        )
        num_rounds = st.slider(
            "Federation Rounds", 1, 100, int(PROJECT_CONFIG["num_rounds"])
        )
        random_seed = st.number_input(
            "Random Seed", 0, 999999, int(PROJECT_CONFIG["random_seed"])
        )

        st.markdown("---")
        st.markdown("**Adversarial Configuration**")
        enable_attack = st.checkbox(
            "Enable Client Attacks", value=bool(PROJECT_CONFIG["attack"]["enabled"])
        )
        client_attacks = {}
        scale_factor = float(PROJECT_CONFIG["attack"]["scale_factor"])

        if enable_attack:
            preset = st.selectbox("Attack Preset:", ["2 Scaling", "2 Label-Flip", "Mixed Attacks", "Custom"])
            configured_malicious_ids = {
                int(cid) for cid in PROJECT_CONFIG["attack"]["malicious_client_ids"]
            }
            if preset == "2 Scaling":
                for i in range(num_clients): client_attacks[i] = "scaling" if i in configured_malicious_ids else "none"
            elif preset == "2 Label-Flip":
                for i in range(num_clients): client_attacks[i] = "label_flip" if i in configured_malicious_ids else "none"
            elif preset == "Mixed Attacks":
                attacks = ["scaling", "label_flip", "sign_flip", "none", "none"]
                for i in range(num_clients): client_attacks[i] = attacks[i] if i < len(attacks) else "none"
            else:
                for i in range(num_clients):
                    client_attacks[i] = st.selectbox(f"Client {i}:", ["none", "scaling", "label_flip", "sign_flip", "backdoor"], key=f"atk_sel_{i}")
            scale_factor = st.slider(
                "Scaling Factor", 1.0, 100.0,
                float(PROJECT_CONFIG["attack"]["scale_factor"]), 1.0
            )
        else:
            for i in range(num_clients): client_attacks[i] = "none"

        st.markdown("---")
        st.markdown("**Autonomous Self-Healing**")
        enable_self_healing = st.checkbox(
            "Enable Self-Healing FSM", value=bool(PROJECT_CONFIG["self_healing"]["enabled"])
        )
        dps_threshold = float(PROJECT_CONFIG["self_healing"]["dps_threshold"])
        recovery_rounds = int(PROJECT_CONFIG["self_healing"]["recovery_rounds"])
        if enable_self_healing:
            dps_threshold = st.slider(
                "DPS Alert Threshold", 0.0, 1.0,
                float(PROJECT_CONFIG["self_healing"]["dps_threshold"]), 0.05
            )
            recovery_rounds = st.slider(
                "Recovery Window (Rounds)", 1, 20,
                int(PROJECT_CONFIG["self_healing"]["recovery_rounds"])
            )

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
                    "dataset_path": PROJECT_CONFIG["dataset_path"],
                    "test_split": PROJECT_CONFIG["test_split"],
                    "iid": PROJECT_CONFIG["iid"],
                    "num_clients_per_round": PROJECT_CONFIG["num_clients_per_round"],
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

    current_attack = st.session_state.get("comparison_attack_label", "Not Run Yet")
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
