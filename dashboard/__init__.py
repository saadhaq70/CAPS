"""Dashboard package for ASH-FL interactive visualization."""

from .simulator import DashboardSimulator
from .dps_calculator import DPSCalculator
from .visualizations import (
    create_accuracy_chart,
    create_loss_chart,
    create_dps_radar,
    create_trust_evolution,
    create_aggregation_heatmap
)
from .explanations import get_explanation_content

__all__ = [
    'DashboardSimulator',
    'DPSCalculator',
    'create_accuracy_chart',
    'create_loss_chart',
    'create_dps_radar',
    'create_trust_evolution',
    'create_aggregation_heatmap',
    'get_explanation_content'
]
