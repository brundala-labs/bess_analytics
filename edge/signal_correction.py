"""
Signal Correction Engine

Corrects SoC/SoE/SoP signals using cell-level data and provides trust scores.
Implements HSL/LSL (High/Low Safety Limits) for safe operating range.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class CorrectedSignals:
    """Container for corrected signal values."""
    site_id: str
    ts: datetime
    soc_pct_raw: float
    soc_pct_corrected: float
    soe_mwh_corrected: float
    sop_charge_kw: float
    sop_discharge_kw: float
    hsl_soc_pct: float  # High Safety Limit
    lsl_soc_pct: float  # Low Safety Limit
    signal_trust_score: float  # 0-100
    drift_detected: bool
    correction_applied: bool


class SignalCorrectionEngine:
    """
    Engine for correcting battery signals using cell-level data.

    Provides:
    - SoC correction based on cell voltage analysis
    - SoE (State of Energy) calculation in MWh
    - SoP (State of Power) limits for charge/discharge
    - HSL/LSL safety bands
    - Signal trust scoring
    """

    def __init__(
        self,
        nominal_capacity_mwh: float,
        max_power_kw: float,
        hsl_default: float = 95.0,
        lsl_default: float = 10.0,
        drift_threshold: float = 2.0,
    ):
        """
        Initialize the signal correction engine.

        Args:
            nominal_capacity_mwh: Nominal battery capacity in MWh
            max_power_kw: Maximum power rating in kW
            hsl_default: Default high safety limit for SoC (%)
            lsl_default: Default low safety limit for SoC (%)
            drift_threshold: Threshold for detecting SoC drift (%)
        """
        self.nominal_capacity_mwh = nominal_capacity_mwh
        self.max_power_kw = max_power_kw
        self.hsl_default = hsl_default
        self.lsl_default = lsl_default
        self.drift_threshold = drift_threshold

    def process(
        self,
        site_id: str,
        ts: datetime,
        soc_pct_raw: float,
        cell_voltages: Optional[list[float]] = None,
        cell_temps: Optional[list[float]] = None,
        ambient_temp: float = 25.0,
    ) -> CorrectedSignals:
        """
        Process raw signals and return corrected values.

        Args:
            site_id: Site identifier
            ts: Timestamp
            soc_pct_raw: Raw SoC percentage from BMS
            cell_voltages: List of cell voltages (mV)
            cell_temps: List of cell temperatures (C)
            ambient_temp: Ambient temperature (C)

        Returns:
            CorrectedSignals with all corrected values and metrics
        """
        # Calculate trust score based on data quality
        trust_score = self._calculate_trust_score(
            cell_voltages, cell_temps, soc_pct_raw
        )

        # Detect drift
        drift_detected = False
        correction_applied = False
        soc_corrected = soc_pct_raw

        if cell_voltages:
            # Estimate SoC from cell voltages
            soc_from_voltage = self._estimate_soc_from_voltage(cell_voltages)
            drift = abs(soc_from_voltage - soc_pct_raw)

            if drift > self.drift_threshold:
                drift_detected = True
                # Blend correction based on trust
                blend_factor = min(drift / 10.0, 0.5)
                soc_corrected = soc_pct_raw * (1 - blend_factor) + soc_from_voltage * blend_factor
                correction_applied = True

        # Calculate dynamic HSL/LSL based on temperature
        hsl, lsl = self._calculate_safety_limits(cell_temps, ambient_temp)

        # Calculate SoE (usable energy)
        soe_mwh = self._calculate_soe(soc_corrected, hsl, lsl)

        # Calculate SoP (power limits)
        sop_charge, sop_discharge = self._calculate_sop(
            soc_corrected, cell_temps, ambient_temp
        )

        return CorrectedSignals(
            site_id=site_id,
            ts=ts,
            soc_pct_raw=soc_pct_raw,
            soc_pct_corrected=soc_corrected,
            soe_mwh_corrected=soe_mwh,
            sop_charge_kw=sop_charge,
            sop_discharge_kw=sop_discharge,
            hsl_soc_pct=hsl,
            lsl_soc_pct=lsl,
            signal_trust_score=trust_score,
            drift_detected=drift_detected,
            correction_applied=correction_applied,
        )

    def _calculate_trust_score(
        self,
        cell_voltages: Optional[list[float]],
        cell_temps: Optional[list[float]],
        soc_raw: float,
    ) -> float:
        """Calculate signal trust score (0-100)."""
        score = 100.0

        # Penalize missing cell data
        if not cell_voltages:
            score -= 20
        if not cell_temps:
            score -= 10

        # Penalize extreme SoC values
        if soc_raw < 5 or soc_raw > 98:
            score -= 10

        # Penalize high cell voltage variance
        if cell_voltages and len(cell_voltages) > 1:
            voltage_std = np.std(cell_voltages)
            if voltage_std > 50:  # mV
                score -= min(voltage_std / 10, 20)

        # Penalize high temperature variance
        if cell_temps and len(cell_temps) > 1:
            temp_std = np.std(cell_temps)
            if temp_std > 3:  # C
                score -= min(temp_std * 3, 15)

        return max(0, min(100, score))

    def _estimate_soc_from_voltage(self, cell_voltages: list[float]) -> float:
        """Estimate SoC from average cell voltage using simplified OCV curve."""
        avg_voltage = np.mean(cell_voltages)

        # Simplified LFP OCV curve (mV to SoC)
        # Real implementation would use proper OCV lookup
        if avg_voltage >= 3400:
            return 100.0
        elif avg_voltage <= 2800:
            return 0.0
        else:
            # Linear interpolation (simplified)
            return (avg_voltage - 2800) / (3400 - 2800) * 100

    def _calculate_safety_limits(
        self,
        cell_temps: Optional[list[float]],
        ambient_temp: float,
    ) -> tuple[float, float]:
        """Calculate dynamic HSL/LSL based on temperature."""
        hsl = self.hsl_default
        lsl = self.lsl_default

        if cell_temps:
            max_temp = max(cell_temps)
            min_temp = min(cell_temps)

            # Reduce HSL at high temperatures
            if max_temp > 35:
                hsl = max(80, self.hsl_default - (max_temp - 35) * 2)

            # Increase LSL at low temperatures
            if min_temp < 10:
                lsl = min(20, self.lsl_default + (10 - min_temp) * 2)

        return hsl, lsl

    def _calculate_soe(self, soc_pct: float, hsl: float, lsl: float) -> float:
        """Calculate usable State of Energy in MWh."""
        # Usable SoC range
        usable_soc = max(0, min(soc_pct, hsl) - lsl)
        usable_range = hsl - lsl

        if usable_range <= 0:
            return 0.0

        # Convert to MWh
        return (usable_soc / 100) * self.nominal_capacity_mwh

    def _calculate_sop(
        self,
        soc_pct: float,
        cell_temps: Optional[list[float]],
        ambient_temp: float,
    ) -> tuple[float, float]:
        """Calculate State of Power limits for charge and discharge."""
        charge_limit = self.max_power_kw
        discharge_limit = self.max_power_kw

        # SoC-based derating
        if soc_pct > 90:
            charge_limit *= (100 - soc_pct) / 10
        if soc_pct < 10:
            discharge_limit *= soc_pct / 10

        # Temperature-based derating
        if cell_temps:
            max_temp = max(cell_temps)
            min_temp = min(cell_temps)

            if max_temp > 40:
                derate = min(0.5, (max_temp - 40) * 0.1)
                charge_limit *= (1 - derate)
                discharge_limit *= (1 - derate)

            if min_temp < 5:
                derate = min(0.5, (5 - min_temp) * 0.1)
                charge_limit *= (1 - derate)

        return charge_limit, discharge_limit
