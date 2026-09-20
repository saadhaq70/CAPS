"""
Visualization functions for dashboard.
Creates interactive Plotly charts.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict


def create_accuracy_chart(results: Dict, detailed: bool = False) -> go.Figure:
    """
    Create accuracy over rounds chart.
    
    Args:
        results: Simulation results dictionary
        detailed: Whether to show detailed view
        
    Returns:
        Plotly figure
    """
    rounds_data = results['rounds']
    rounds = [r['round'] for r in rounds_data]
    accuracies = [r['metrics']['accuracy'] for r in rounds_data]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=rounds,
        y=accuracies,
        mode='lines+markers',
        name='Accuracy',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8),
        hovertemplate='Round %{x}<br>Accuracy: %{y:.3f}<extra></extra>'
    ))
    
    # Add average line
    avg_acc = np.mean(accuracies)
    fig.add_hline(y=avg_acc, line_dash="dash", line_color="gray",
                 annotation_text=f"Average: {avg_acc:.3f}")
    
    fig.update_layout(
        title="Global Model Accuracy Over Rounds",
        xaxis_title="Round",
        yaxis_title="Accuracy",
        hovermode='x unified',
        template='plotly_white',
        height=400 if not detailed else 500
    )
    
    return fig


def create_loss_chart(results: Dict, detailed: bool = False) -> go.Figure:
    """
    Create loss over rounds chart.
    
    Args:
        results: Simulation results dictionary
        detailed: Whether to show detailed view
        
    Returns:
        Plotly figure
    """
    rounds_data = results['rounds']
    rounds = [r['round'] for r in rounds_data]
    losses = [r['metrics']['loss'] for r in rounds_data]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=rounds,
        y=losses,
        mode='lines+markers',
        name='Loss',
        line=dict(color='#ff7f0e', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(255, 127, 14, 0.1)',
        hovertemplate='Round %{x}<br>Loss: %{y:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Global Model Loss Over Rounds",
        xaxis_title="Round",
        yaxis_title="Loss",
        hovermode='x unified',
        template='plotly_white',
        height=400 if not detailed else 500
    )
    
    return fig


def create_dps_radar(signal_scores: Dict[str, float], is_malicious: bool = False) -> go.Figure:
    """
    Create radar chart for DPS signal breakdown.
    
    Args:
        signal_scores: Dictionary with G, C, H, P, D scores
        is_malicious: Whether client is malicious
        
    Returns:
        Plotly figure
    """
    categories = ['G<br>(Gradient)', 'C<br>(Cosine)', 'H<br>(History)',
                 'P<br>(Performance)', 'D<br>(Data Quality)']
    values = [signal_scores['G'], signal_scores['C'], signal_scores['H'],
             signal_scores['P'], signal_scores['D']]
    
    # Close the radar
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]
    
    color = 'red' if is_malicious else 'green'
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor=f'rgba(255, 0, 0, 0.2)' if is_malicious else 'rgba(0, 255, 0, 0.2)',
        line=dict(color=color, width=2),
        name='Signal Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(values + [1.0])])
        ),
        showlegend=False,
        title=f"DPS Signal Breakdown {'(Malicious)' if is_malicious else '(Honest)'}",
        height=400
    )
    
    return fig


def create_trust_evolution(results: Dict) -> go.Figure:
    """
    Create trust score evolution chart for all clients.
    
    Args:
        results: Simulation results dictionary
        
    Returns:
        Plotly figure
    """
    rounds_data = results['rounds']
    ground_truth = results['ground_truth']
    
    fig = go.Figure()
    
    # Get all client IDs
    client_ids = sorted(rounds_data[0]['trust_scores'].keys())
    
    for cid in client_ids:
        rounds = [r['round'] for r in rounds_data]
        trust_scores = [r['trust_scores'].get(cid, 1.0) for r in rounds_data]
        
        is_malicious = ground_truth.get(cid, False)
        color = 'red' if is_malicious else 'green'
        dash = 'dash' if is_malicious else 'solid'
        
        fig.add_trace(go.Scatter(
            x=rounds,
            y=trust_scores,
            mode='lines+markers',
            name=f'Client {cid} {"(Malicious)" if is_malicious else "(Honest)"}',
            line=dict(color=color, dash=dash, width=2),
            marker=dict(size=6),
            hovertemplate=f'Client {cid}<br>Round: %{{x}}<br>Trust: %{{y:.4f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Trust Score Evolution by Client",
        xaxis_title="Round",
        yaxis_title="Trust Score",
        hovermode='x unified',
        template='plotly_white',
        height=500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig


def create_aggregation_heatmap(results: Dict) -> go.Figure:
    """
    Create heatmap of aggregation weights over rounds.
    
    Args:
        results: Simulation results dictionary
        
    Returns:
        Plotly figure
    """
    rounds_data = results['rounds']
    ground_truth = results['ground_truth']
    
    # Build matrix: clients x rounds
    client_ids = sorted(rounds_data[0]['aggregation_weights'].keys())
    rounds = [r['round'] for r in rounds_data]
    
    weight_matrix = []
    for cid in client_ids:
        weights = [r['aggregation_weights'].get(cid, 0.0) for r in rounds_data]
        weight_matrix.append(weights)
    
    # Create labels with status
    y_labels = [f"Client {cid} {'🔴' if ground_truth.get(cid, False) else '✅'}"
               for cid in client_ids]
    
    fig = go.Figure(data=go.Heatmap(
        z=weight_matrix,
        x=rounds,
        y=y_labels,
        colorscale='Viridis',
        hovertemplate='Round: %{x}<br>Client: %{y}<br>Weight: %{z:.4f}<extra></extra>',
        colorbar=dict(title="Weight")
    ))
    
    fig.update_layout(
        title="Aggregation Weights Heatmap (Green=Honest, Red=Malicious)",
        xaxis_title="Round",
        yaxis_title="Client",
        height=400,
        template='plotly_white'
    )
    
    return fig


def create_comparison_bars(results: Dict) -> go.Figure:
    """
    Create bar chart comparing final metrics.
    
    Args:
        results: Simulation results dictionary
        
    Returns:
        Plotly figure
    """
    final_round = results['rounds'][-1]
    
    categories = ['Accuracy', 'Loss', 'Avg DPS', 'Max DPS']
    values = [
        final_round['metrics']['accuracy'],
        final_round['metrics']['loss'],
        np.mean(list(final_round['dps_scores'].values())),
        max(final_round['dps_scores'].values())
    ]
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
            text=[f'{v:.3f}' for v in values],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Final Metrics Summary",
        yaxis_title="Value",
        template='plotly_white',
        height=400
    )
    
    return fig
