"""
Visualizations for Defense Comparison.
Provides clean, minimal, research-grade Plotly charts for academic presentation:
- Final Accuracy Bar Chart
- Accuracy vs Round Multi-line Chart
- Loss vs Round Multi-line Chart
- Accuracy Degradation Comparison Chart
- Backdoor ASR Chart
"""

from typing import Any, Dict, Optional
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Defense theme palette: clean academic contrast
DEFENSE_COLORS = {
    "ASH-FL": "#6366f1",         # Indigo / Primary proposed defense
    "Multi-Krum": "#0284c7",     # Sky blue
    "Trimmed Mean": "#d97706",   # Amber
    "FLTrust": "#059669",        # Emerald
}

ACADEMIC_LAYOUT = dict(
    paper_bgcolor="rgba(15, 23, 42, 0.4)",
    plot_bgcolor="rgba(0, 0, 0, 0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", color="#94a3b8"),
    margin=dict(l=45, r=45, t=50, b=45),
)


def create_client_trust_timeline(
    per_round_metrics: list[Dict[str, Any]],
    num_clients: int,
    title: str = "Client Trust Score by Round",
) -> go.Figure:
    """Plot recorded ASH-FL trust scores and actual quarantine actions by round."""
    rounds = list(range(1, len(per_round_metrics) + 1))
    fig = go.Figure()
    client_trust = {client_id: [] for client_id in range(num_clients)}
    quarantine_points = {client_id: ([], []) for client_id in range(num_clients)}

    for round_number, metrics in zip(rounds, per_round_metrics):
        trust_scores = {
            int(client_id): float(score)
            for client_id, score in metrics.get("trust_scores", {}).items()
            if 0 <= int(client_id) < num_clients
        }
        quarantined = {int(cid) for cid in metrics.get("quarantined_clients", [])}
        for client_id in range(num_clients):
            trust = trust_scores.get(client_id)
            client_trust[client_id].append(trust)
            if trust is not None and client_id in quarantined:
                quarantine_points[client_id][0].append(round_number)
                quarantine_points[client_id][1].append(trust)

    palette = ["#c7f36b", "#70c6bc", "#a894f4", "#f2a65a", "#68a9e8", "#ed7892", "#d9cb70", "#8cda92"]
    for client_id, values in client_trust.items():
        color = palette[client_id % len(palette)]
        fig.add_trace(go.Scatter(
            x=rounds,
            y=values,
            mode="lines+markers",
            name=f"Client {client_id}",
            connectgaps=False,
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color),
            hovertemplate=f"<b>Client {client_id}</b><br>Round %{{x}}<br>Trust %{{y:.3f}}<extra></extra>",
        ))
        quarantine_x, quarantine_y = quarantine_points[client_id]
        if quarantine_x:
            fig.add_trace(go.Scatter(
                x=quarantine_x, y=quarantine_y, mode="markers", name=f"Client {client_id} quarantined",
                legendgroup=f"client-{client_id}", showlegend=False,
                marker=dict(symbol="diamond", size=11, color="#ffbd59", line=dict(color="#171a15", width=1)),
                hovertemplate=f"<b>Client {client_id} · quarantined</b><br>Round %{{x}}<br>Trust %{{y:.3f}}<extra></extra>",
            ))

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="#f0f0e9")),
        xaxis=dict(title="Federated round", dtick=1, gridcolor="rgba(190,200,170,.10)", color="#a9afa0"),
        yaxis=dict(title="Client trust score", range=[0, 1], gridcolor="rgba(190,200,170,.10)", color="#a9afa0"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#a9afa0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=55, r=25, t=75, b=50), height=430,
        hovermode="x unified",
    )
    return fig


def create_comparison_accuracy_bar(defense_results: Dict[str, Any]) -> go.Figure:
    """Bar chart comparing final accuracy across defenses."""
    defenses = list(defense_results.keys())
    accuracies = [defense_results[d].final_accuracy for d in defenses]
    colors = [DEFENSE_COLORS.get(d, "#6366f1") for d in defenses]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=defenses,
        y=[a * 100 for a in accuracies],
        marker=dict(
            color=colors,
            line=dict(color="#334155", width=1),
        ),
        text=[f"{a:.1%}" for a in accuracies],
        textposition="outside",
        textfont=dict(size=12, color="#f8fafc", family="Inter, sans-serif"),
        hovertemplate="<b>%{x}</b><br>Final Accuracy: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="<b>Final Model Accuracy by Defense</b>", font=dict(size=14, color="#f8fafc")),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.1)",
            tickfont=dict(color="#cbd5e1", size=12),
        ),
        yaxis=dict(
            title="Accuracy (%)",
            range=[0, 105],
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#94a3b8", size=11),
        ),
        **ACADEMIC_LAYOUT,
        height=380,
    )
    return fig


def create_comparison_accuracy_trajectory(defense_results: Dict[str, Any]) -> go.Figure:
    """Multi-line trajectory of accuracy vs federated rounds."""
    fig = go.Figure()

    for name, res in defense_results.items():
        rounds = list(range(1, len(res.per_round_accuracy) + 1))
        color = DEFENSE_COLORS.get(name, "#6366f1")
        fig.add_trace(go.Scatter(
            x=rounds,
            y=[acc * 100 for acc in res.per_round_accuracy],
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, symbol="circle", line=dict(color="#1e293b", width=1)),
            hovertemplate=f"<b>{name}</b><br>Round %{{x}}<br>Accuracy: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="<b>Accuracy Trajectory (Rounds 1–3)</b>", font=dict(size=14, color="#f8fafc")),
        xaxis=dict(
            title="Federated Round",
            dtick=1,
            gridcolor="rgba(148, 163, 184, 0.1)",
            tickfont=dict(color="#cbd5e1", size=11),
        ),
        yaxis=dict(
            title="Test Accuracy (%)",
            range=[0, 105],
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#94a3b8", size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1", size=11),
        ),
        **ACADEMIC_LAYOUT,
        height=380,
    )
    return fig


def create_comparison_loss_trajectory(defense_results: Dict[str, Any]) -> go.Figure:
    """Multi-line trajectory of loss vs federated rounds."""
    fig = go.Figure()

    for name, res in defense_results.items():
        rounds = list(range(1, len(res.per_round_loss) + 1))
        color = DEFENSE_COLORS.get(name, "#6366f1")
        fig.add_trace(go.Scatter(
            x=rounds,
            y=res.per_round_loss,
            mode="lines+markers",
            name=name,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, symbol="diamond", line=dict(color="#1e293b", width=1)),
            hovertemplate=f"<b>{name}</b><br>Round %{{x}}<br>Loss: %{{y:.4f}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="<b>Loss Convergence Across Rounds</b>", font=dict(size=14, color="#f8fafc")),
        xaxis=dict(
            title="Federated Round",
            dtick=1,
            gridcolor="rgba(148, 163, 184, 0.1)",
            tickfont=dict(color="#cbd5e1", size=11),
        ),
        yaxis=dict(
            title="Cross-Entropy Loss",
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#94a3b8", size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1", size=11),
        ),
        **ACADEMIC_LAYOUT,
        height=380,
    )
    return fig


def create_comparison_degradation_chart(defense_results: Dict[str, Any]) -> go.Figure:
    """Grouped bar chart comparing Clean Baseline vs Attacked Accuracy."""
    defenses = list(defense_results.keys())
    clean_accs = [defense_results[d].clean_accuracy * 100 for d in defenses]
    attacked_accs = [defense_results[d].final_accuracy * 100 for d in defenses]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=defenses,
        y=clean_accs,
        name="Clean Baseline",
        marker_color="rgba(16, 185, 129, 0.7)",
        marker_line=dict(color="#059669", width=1),
        text=[f"{v:.1f}%" for v in clean_accs],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=defenses,
        y=attacked_accs,
        name="Under Attack",
        marker_color="rgba(244, 63, 94, 0.7)",
        marker_line=dict(color="#e11d48", width=1),
        text=[f"{v:.1f}%" for v in attacked_accs],
        textposition="outside",
    ))

    fig.update_layout(
        title=dict(text="<b>Accuracy Degradation: Clean vs. Under Attack</b>", font=dict(size=14, color="#f8fafc")),
        barmode="group",
        xaxis=dict(gridcolor="rgba(148, 163, 184, 0.1)", tickfont=dict(color="#cbd5e1", size=11)),
        yaxis=dict(
            title="Accuracy (%)",
            range=[0, 110],
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#94a3b8", size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1", size=11),
        ),
        **ACADEMIC_LAYOUT,
        height=380,
    )
    return fig


def create_comparison_backdoor_asr_chart(defense_results: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Bar chart showing Backdoor Attack Success Rate (ASR).
    Lower ASR is better (green), higher ASR indicates backdoor trojan susceptibility (amber/rose).
    """
    defenses = []
    asrs = []
    for d, res in defense_results.items():
        if res.backdoor_asr is not None:
            defenses.append(d)
            asrs.append(res.backdoor_asr * 100)

    if not defenses:
        return None

    colors = []
    for asr in asrs:
        if asr < 15.0:
            colors.append("#10b981")  # Low risk (good resistance)
        elif asr < 25.0:
            colors.append("#f59e0b")  # Moderate
        else:
            colors.append("#ef4444")  # High vulnerability

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=defenses,
        y=asrs,
        marker=dict(
            color=colors,
            line=dict(color="#334155", width=1),
        ),
        text=[f"{a:.1f}%" for a in asrs],
        textposition="outside",
        textfont=dict(size=12, color="#f8fafc"),
        hovertemplate="<b>%{x}</b><br>Backdoor ASR: %{y:.1f}%<br>(Lower is Better)<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="<b>Backdoor Attack Success Rate (ASR) — Lower is Better</b>", font=dict(size=14, color="#f8fafc")),
        xaxis=dict(gridcolor="rgba(148, 163, 184, 0.1)", tickfont=dict(color="#cbd5e1", size=12)),
        yaxis=dict(
            title="Attack Success Rate (ASR %)",
            range=[0, max(max(asrs) + 15, 30)],
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#94a3b8", size=11),
        ),
        **ACADEMIC_LAYOUT,
        height=360,
    )
    return fig


def create_attack_defense_accuracy_heatmap(
    matrix_results: Dict[str, Any],
) -> go.Figure:
    """Show final accuracy for every attack-by-defense result in a matrix run."""
    attack_order = ["label_flip", "sign_flip", "scaling", "backdoor"]
    attack_labels = {
        "label_flip": "Label Flip",
        "sign_flip": "Sign Flip",
        "scaling": "Scaling",
        "backdoor": "Backdoor",
    }
    defense_order = ["ASH-FL", "Multi-Krum", "Trimmed Mean", "FLTrust"]

    attacks = [attack for attack in attack_order if attack in matrix_results]
    defenses = [
        defense for defense in defense_order
        if any(defense in matrix_results[attack].defense_results for attack in attacks)
    ]
    values = [
        [
            matrix_results[attack].defense_results[defense].final_accuracy * 100
            if defense in matrix_results[attack].defense_results else np.nan
            for defense in defenses
        ]
        for attack in attacks
    ]
    labels = [
        [f"{value:.1f}%" if np.isfinite(value) else "" for value in row]
        for row in values
    ]

    fig = go.Figure(go.Heatmap(
        z=values,
        x=defenses,
        y=[attack_labels[attack] for attack in attacks],
        text=labels,
        texttemplate="%{text}",
        textfont=dict(color="#f8fafc", size=13),
        colorscale="Viridis",
        zmin=0,
        zmax=100,
        colorbar=dict(title="Accuracy (%)", tickfont=dict(color="#cbd5e1")),
        hovertemplate="Attack: %{y}<br>Defense: %{x}<br>Final accuracy: %{z:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="<b>Final Accuracy: All Attacks × All Defenses</b>", font=dict(size=15, color="#f8fafc")),
        xaxis=dict(title="Defense strategy", tickfont=dict(color="#cbd5e1")),
        yaxis=dict(title="Attack scenario", autorange="reversed", tickfont=dict(color="#cbd5e1")),
        **ACADEMIC_LAYOUT,
        height=390,
    )
    return fig
