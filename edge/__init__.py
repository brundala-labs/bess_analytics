"""
Edge Intelligence Package

Provides advanced analytics engines for BESS operations:
- Signal Correction: SoC/SoE/SoP correction with trust scores
- Forecasting: Time-to-empty/full predictions
- Balancing: Rack imbalance detection and actions
- Insights: Automated findings generation
"""

from edge.signal_correction import SignalCorrectionEngine
from edge.forecasting import ForecastEngine
from edge.balancing import BalancingEngine
from edge.insights import InsightsEngine

__all__ = [
    "SignalCorrectionEngine",
    "ForecastEngine",
    "BalancingEngine",
    "InsightsEngine",
]
