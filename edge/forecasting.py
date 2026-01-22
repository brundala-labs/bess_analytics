"""
Forecasting Engine

Predicts time-to-empty/full and energy availability at multiple horizons.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np


@dataclass
class EnergyForecast:
    """Container for energy forecast results."""
    site_id: str
    ts: datetime
    horizon_min: int
    predicted_soc_pct: float
    time_to_empty_min: Optional[float]
    time_to_full_min: Optional[float]
    confidence_pct: float
    available_energy_mwh: float
    available_power_kw: float


class ForecastEngine:
    """
    Engine for predicting energy and power availability.

    Provides:
    - Time-to-empty predictions
    - Time-to-full predictions
    - Multi-horizon SoC forecasts
    - Confidence intervals
    """

    def __init__(
        self,
        nominal_capacity_mwh: float,
        max_power_kw: float,
        min_soc_pct: float = 10.0,
        max_soc_pct: float = 95.0,
    ):
        """
        Initialize the forecasting engine.

        Args:
            nominal_capacity_mwh: Nominal battery capacity in MWh
            max_power_kw: Maximum power rating in kW
            min_soc_pct: Minimum operational SoC (%)
            max_soc_pct: Maximum operational SoC (%)
        """
        self.nominal_capacity_mwh = nominal_capacity_mwh
        self.max_power_kw = max_power_kw
        self.min_soc_pct = min_soc_pct
        self.max_soc_pct = max_soc_pct

    def forecast(
        self,
        site_id: str,
        ts: datetime,
        current_soc_pct: float,
        current_power_kw: float,
        horizon_minutes: list[int] = None,
        power_forecast_kw: Optional[list[float]] = None,
    ) -> list[EnergyForecast]:
        """
        Generate energy forecasts at multiple horizons.

        Args:
            site_id: Site identifier
            ts: Current timestamp
            current_soc_pct: Current SoC (%)
            current_power_kw: Current power (kW, positive=discharge)
            horizon_minutes: List of forecast horizons in minutes
            power_forecast_kw: Optional power forecast for each horizon

        Returns:
            List of EnergyForecast objects for each horizon
        """
        if horizon_minutes is None:
            horizon_minutes = [15, 30, 60, 120, 240]

        forecasts = []
        for i, horizon in enumerate(horizon_minutes):
            # Use forecasted power if available, else assume current power continues
            power_kw = (
                power_forecast_kw[i]
                if power_forecast_kw and i < len(power_forecast_kw)
                else current_power_kw
            )

            forecast = self._forecast_single_horizon(
                site_id=site_id,
                ts=ts,
                current_soc_pct=current_soc_pct,
                power_kw=power_kw,
                horizon_min=horizon,
            )
            forecasts.append(forecast)

        return forecasts

    def _forecast_single_horizon(
        self,
        site_id: str,
        ts: datetime,
        current_soc_pct: float,
        power_kw: float,
        horizon_min: int,
    ) -> EnergyForecast:
        """Generate forecast for a single horizon."""
        # Calculate energy change over horizon
        hours = horizon_min / 60.0
        energy_change_mwh = (power_kw / 1000) * hours  # positive = discharge

        # Calculate predicted SoC
        soc_change_pct = (energy_change_mwh / self.nominal_capacity_mwh) * 100
        predicted_soc = current_soc_pct - soc_change_pct  # discharge reduces SoC

        # Clamp to valid range
        predicted_soc = max(0, min(100, predicted_soc))

        # Calculate time-to-empty and time-to-full
        time_to_empty = None
        time_to_full = None

        if power_kw > 0:  # Discharging
            usable_soc = current_soc_pct - self.min_soc_pct
            if usable_soc > 0 and power_kw > 0:
                usable_energy_mwh = (usable_soc / 100) * self.nominal_capacity_mwh
                time_to_empty = (usable_energy_mwh / (power_kw / 1000)) * 60  # minutes

        elif power_kw < 0:  # Charging
            remaining_soc = self.max_soc_pct - current_soc_pct
            if remaining_soc > 0 and power_kw < 0:
                remaining_energy_mwh = (remaining_soc / 100) * self.nominal_capacity_mwh
                time_to_full = (remaining_energy_mwh / (abs(power_kw) / 1000)) * 60  # minutes

        # Calculate available energy (above min SoC)
        available_soc = max(0, predicted_soc - self.min_soc_pct)
        available_energy_mwh = (available_soc / 100) * self.nominal_capacity_mwh

        # Calculate available power (with SoC derating)
        available_power_kw = self._calculate_available_power(predicted_soc)

        # Calculate confidence (decreases with horizon)
        confidence = self._calculate_confidence(horizon_min, power_kw)

        return EnergyForecast(
            site_id=site_id,
            ts=ts,
            horizon_min=horizon_min,
            predicted_soc_pct=predicted_soc,
            time_to_empty_min=time_to_empty,
            time_to_full_min=time_to_full,
            confidence_pct=confidence,
            available_energy_mwh=available_energy_mwh,
            available_power_kw=available_power_kw,
        )

    def _calculate_available_power(self, soc_pct: float) -> float:
        """Calculate available power based on SoC."""
        if soc_pct <= self.min_soc_pct:
            return 0.0
        elif soc_pct >= self.max_soc_pct:
            return self.max_power_kw

        # Linear derating near limits
        if soc_pct < self.min_soc_pct + 10:
            return self.max_power_kw * (soc_pct - self.min_soc_pct) / 10

        return self.max_power_kw

    def _calculate_confidence(self, horizon_min: int, power_kw: float) -> float:
        """Calculate forecast confidence."""
        # Base confidence decreases with horizon
        base_confidence = 100 - (horizon_min / 10)

        # Lower confidence at high power (more uncertainty)
        power_factor = 1 - min(abs(power_kw) / self.max_power_kw * 0.1, 0.2)

        return max(50, min(100, base_confidence * power_factor))
