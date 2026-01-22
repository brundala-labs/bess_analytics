"""
Balancing Engine

Detects rack-level imbalances and generates balancing action recommendations.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

import numpy as np


class ImbalanceSeverity(Enum):
    """Severity levels for imbalance detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionPriority(Enum):
    """Priority levels for balancing actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class RackImbalance:
    """Container for rack imbalance detection results."""
    site_id: str
    rack_id: str
    ts: datetime
    imbalance_score: float  # 0-100
    severity: ImbalanceSeverity
    max_cell_delta_mv: float
    max_temp_delta_c: float
    weakest_cell_id: Optional[str]
    strongest_cell_id: Optional[str]


@dataclass
class BalancingAction:
    """Container for recommended balancing action."""
    action_id: str
    site_id: str
    rack_id: str
    ts: datetime
    action_type: str
    priority: ActionPriority
    description: str
    estimated_duration_min: int
    estimated_recovery_mwh: float
    status: str = "pending"


class BalancingEngine:
    """
    Engine for detecting imbalances and generating balancing recommendations.

    Provides:
    - Rack-level imbalance detection
    - Cell-level analysis
    - Balancing action recommendations
    - Priority-based action queue
    """

    def __init__(
        self,
        voltage_imbalance_threshold_mv: float = 50.0,
        temp_imbalance_threshold_c: float = 5.0,
        critical_voltage_delta_mv: float = 100.0,
        critical_temp_delta_c: float = 10.0,
    ):
        """
        Initialize the balancing engine.

        Args:
            voltage_imbalance_threshold_mv: Voltage delta threshold for detection (mV)
            temp_imbalance_threshold_c: Temperature delta threshold for detection (C)
            critical_voltage_delta_mv: Critical voltage delta threshold (mV)
            critical_temp_delta_c: Critical temperature delta threshold (C)
        """
        self.voltage_threshold = voltage_imbalance_threshold_mv
        self.temp_threshold = temp_imbalance_threshold_c
        self.critical_voltage = critical_voltage_delta_mv
        self.critical_temp = critical_temp_delta_c

    def analyze_rack(
        self,
        site_id: str,
        rack_id: str,
        ts: datetime,
        cell_voltages: list[float],
        cell_temps: list[float],
        cell_ids: Optional[list[str]] = None,
    ) -> RackImbalance:
        """
        Analyze a rack for imbalances.

        Args:
            site_id: Site identifier
            rack_id: Rack identifier
            ts: Timestamp
            cell_voltages: List of cell voltages (mV)
            cell_temps: List of cell temperatures (C)
            cell_ids: Optional list of cell identifiers

        Returns:
            RackImbalance with detection results
        """
        # Calculate deltas
        voltage_delta = max(cell_voltages) - min(cell_voltages)
        temp_delta = max(cell_temps) - min(cell_temps)

        # Find weakest and strongest cells
        weakest_idx = np.argmin(cell_voltages)
        strongest_idx = np.argmax(cell_voltages)

        weakest_cell = cell_ids[weakest_idx] if cell_ids else f"cell_{weakest_idx}"
        strongest_cell = cell_ids[strongest_idx] if cell_ids else f"cell_{strongest_idx}"

        # Calculate imbalance score (0-100)
        voltage_score = min(100, (voltage_delta / self.critical_voltage) * 50)
        temp_score = min(100, (temp_delta / self.critical_temp) * 50)
        imbalance_score = (voltage_score + temp_score) / 2

        # Determine severity
        severity = self._determine_severity(voltage_delta, temp_delta)

        return RackImbalance(
            site_id=site_id,
            rack_id=rack_id,
            ts=ts,
            imbalance_score=imbalance_score,
            severity=severity,
            max_cell_delta_mv=voltage_delta,
            max_temp_delta_c=temp_delta,
            weakest_cell_id=weakest_cell,
            strongest_cell_id=strongest_cell,
        )

    def generate_actions(
        self,
        imbalance: RackImbalance,
        nominal_capacity_mwh: float,
    ) -> list[BalancingAction]:
        """
        Generate balancing actions based on imbalance analysis.

        Args:
            imbalance: RackImbalance from analyze_rack
            nominal_capacity_mwh: Rack nominal capacity in MWh

        Returns:
            List of recommended BalancingAction objects
        """
        actions = []

        if imbalance.severity == ImbalanceSeverity.LOW:
            return actions  # No action needed

        # Determine action type and priority based on severity
        if imbalance.severity == ImbalanceSeverity.CRITICAL:
            priority = ActionPriority.URGENT
            action_type = "immediate_balancing"
            duration = 120
            description = (
                f"Critical imbalance detected. Voltage delta: {imbalance.max_cell_delta_mv:.0f}mV, "
                f"Temp delta: {imbalance.max_temp_delta_c:.1f}C. Immediate passive balancing required."
            )
        elif imbalance.severity == ImbalanceSeverity.HIGH:
            priority = ActionPriority.HIGH
            action_type = "scheduled_balancing"
            duration = 240
            description = (
                f"High imbalance detected. Voltage delta: {imbalance.max_cell_delta_mv:.0f}mV. "
                f"Schedule balancing cycle within 24 hours."
            )
        else:  # MEDIUM
            priority = ActionPriority.MEDIUM
            action_type = "monitoring"
            duration = 60
            description = (
                f"Moderate imbalance detected. Voltage delta: {imbalance.max_cell_delta_mv:.0f}mV. "
                f"Increase monitoring frequency and plan maintenance."
            )

        # Estimate energy recovery
        recovery_factor = imbalance.imbalance_score / 100 * 0.02  # Up to 2% capacity
        estimated_recovery = nominal_capacity_mwh * recovery_factor

        actions.append(
            BalancingAction(
                action_id=str(uuid.uuid4())[:8],
                site_id=imbalance.site_id,
                rack_id=imbalance.rack_id,
                ts=imbalance.ts,
                action_type=action_type,
                priority=priority,
                description=description,
                estimated_duration_min=duration,
                estimated_recovery_mwh=estimated_recovery,
            )
        )

        # Add thermal action if temperature imbalance is significant
        if imbalance.max_temp_delta_c > self.temp_threshold:
            actions.append(
                BalancingAction(
                    action_id=str(uuid.uuid4())[:8],
                    site_id=imbalance.site_id,
                    rack_id=imbalance.rack_id,
                    ts=imbalance.ts,
                    action_type="thermal_management",
                    priority=ActionPriority.HIGH if imbalance.max_temp_delta_c > self.critical_temp else ActionPriority.MEDIUM,
                    description=(
                        f"Temperature imbalance of {imbalance.max_temp_delta_c:.1f}C detected. "
                        f"Review HVAC settings and airflow distribution."
                    ),
                    estimated_duration_min=30,
                    estimated_recovery_mwh=0.0,
                )
            )

        return actions

    def _determine_severity(
        self, voltage_delta: float, temp_delta: float
    ) -> ImbalanceSeverity:
        """Determine imbalance severity based on deltas."""
        if voltage_delta >= self.critical_voltage or temp_delta >= self.critical_temp:
            return ImbalanceSeverity.CRITICAL
        elif voltage_delta >= self.voltage_threshold * 1.5 or temp_delta >= self.temp_threshold * 1.5:
            return ImbalanceSeverity.HIGH
        elif voltage_delta >= self.voltage_threshold or temp_delta >= self.temp_threshold:
            return ImbalanceSeverity.MEDIUM
        else:
            return ImbalanceSeverity.LOW
