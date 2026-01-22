"""
Insights Engine

Generates automated findings and recommendations with estimated value impact.
Consolidates insights from all Edge Intelligence engines.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class InsightSeverity(Enum):
    """Severity levels for insights."""
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


class InsightCategory(Enum):
    """Categories for insights."""
    SIGNAL_QUALITY = "signal_quality"
    ENERGY_AVAILABILITY = "energy_availability"
    POWER_CONSTRAINTS = "power_constraints"
    CELL_IMBALANCE = "cell_imbalance"
    THERMAL = "thermal"
    OPERATIONAL = "operational"


@dataclass
class InsightFinding:
    """Container for an automated insight finding."""
    finding_id: str
    ts: datetime
    site_id: str
    category: InsightCategory
    severity: InsightSeverity
    title: str
    description: str
    recommendation: str
    estimated_value_gbp: float
    confidence: float  # 0-1
    acknowledged: bool = False
    resolved: bool = False


class InsightsEngine:
    """
    Engine for generating automated insights from Edge Intelligence data.

    Provides:
    - Automated finding generation
    - Value impact estimation
    - Recommendation generation
    - Insight prioritization
    """

    def __init__(
        self,
        site_capacity_mwh: float,
        revenue_per_mwh_gbp: float = 100.0,
    ):
        """
        Initialize the insights engine.

        Args:
            site_capacity_mwh: Site capacity in MWh
            revenue_per_mwh_gbp: Estimated revenue per MWh for value calculations
        """
        self.site_capacity_mwh = site_capacity_mwh
        self.revenue_per_mwh = revenue_per_mwh_gbp

    def analyze(
        self,
        site_id: str,
        ts: datetime,
        trust_score: float,
        soc_drift: float,
        time_to_empty_min: Optional[float],
        sop_charge_kw: float,
        sop_discharge_kw: float,
        max_power_kw: float,
        imbalance_score: float,
        max_temp_c: float,
        avg_temp_c: float,
    ) -> list[InsightFinding]:
        """
        Analyze current state and generate insights.

        Args:
            site_id: Site identifier
            ts: Current timestamp
            trust_score: Signal trust score (0-100)
            soc_drift: Detected SoC drift (%)
            time_to_empty_min: Time to empty in minutes
            sop_charge_kw: Current charge power limit
            sop_discharge_kw: Current discharge power limit
            max_power_kw: Nominal maximum power
            imbalance_score: Rack imbalance score (0-100)
            max_temp_c: Maximum temperature
            avg_temp_c: Average temperature

        Returns:
            List of InsightFinding objects
        """
        findings = []

        # Signal Quality Insights
        if trust_score < 70:
            findings.append(self._create_signal_quality_finding(
                site_id, ts, trust_score, soc_drift
            ))

        # Energy Availability Insights
        if time_to_empty_min and time_to_empty_min < 60:
            findings.append(self._create_energy_availability_finding(
                site_id, ts, time_to_empty_min
            ))

        # Power Constraints Insights
        power_derate = 1 - (min(sop_charge_kw, sop_discharge_kw) / max_power_kw)
        if power_derate > 0.1:
            findings.append(self._create_power_constraint_finding(
                site_id, ts, power_derate, sop_charge_kw, sop_discharge_kw, max_power_kw
            ))

        # Cell Imbalance Insights
        if imbalance_score > 30:
            findings.append(self._create_imbalance_finding(
                site_id, ts, imbalance_score
            ))

        # Thermal Insights
        if max_temp_c > 40 or (max_temp_c - avg_temp_c) > 5:
            findings.append(self._create_thermal_finding(
                site_id, ts, max_temp_c, avg_temp_c
            ))

        return findings

    def _create_signal_quality_finding(
        self,
        site_id: str,
        ts: datetime,
        trust_score: float,
        soc_drift: float,
    ) -> InsightFinding:
        """Create signal quality insight."""
        if trust_score < 50:
            severity = InsightSeverity.CRITICAL
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.05
        elif trust_score < 60:
            severity = InsightSeverity.ALERT
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.03
        else:
            severity = InsightSeverity.WARNING
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.01

        return InsightFinding(
            finding_id=str(uuid.uuid4())[:8],
            ts=ts,
            site_id=site_id,
            category=InsightCategory.SIGNAL_QUALITY,
            severity=severity,
            title=f"Signal Trust Score Degraded to {trust_score:.0f}%",
            description=(
                f"The signal trust score has dropped to {trust_score:.0f}%, indicating potential "
                f"measurement issues. SoC drift of {soc_drift:.1f}% detected between BMS and "
                f"calculated values."
            ),
            recommendation=(
                "Review BMS calibration and cell-level data quality. Consider recalibrating "
                "SoC estimation if drift persists. Check for communication issues with BMS."
            ),
            estimated_value_gbp=value_impact,
            confidence=0.85,
        )

    def _create_energy_availability_finding(
        self,
        site_id: str,
        ts: datetime,
        time_to_empty_min: float,
    ) -> InsightFinding:
        """Create energy availability insight."""
        if time_to_empty_min < 30:
            severity = InsightSeverity.CRITICAL
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.1
        else:
            severity = InsightSeverity.ALERT
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.05

        return InsightFinding(
            finding_id=str(uuid.uuid4())[:8],
            ts=ts,
            site_id=site_id,
            category=InsightCategory.ENERGY_AVAILABILITY,
            severity=severity,
            title=f"Low Energy Reserve: {time_to_empty_min:.0f} Minutes to Empty",
            description=(
                f"At current discharge rate, battery will reach minimum SoC in "
                f"{time_to_empty_min:.0f} minutes. This may impact ability to deliver "
                f"contracted services."
            ),
            recommendation=(
                "Consider reducing discharge rate or scheduling charge cycle. Review "
                "dispatch schedule and upcoming commitments. Alert trading desk if "
                "service delivery is at risk."
            ),
            estimated_value_gbp=value_impact,
            confidence=0.9,
        )

    def _create_power_constraint_finding(
        self,
        site_id: str,
        ts: datetime,
        power_derate: float,
        sop_charge: float,
        sop_discharge: float,
        max_power: float,
    ) -> InsightFinding:
        """Create power constraint insight."""
        derate_pct = power_derate * 100

        if derate_pct > 30:
            severity = InsightSeverity.CRITICAL
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * power_derate * 0.5
        elif derate_pct > 20:
            severity = InsightSeverity.ALERT
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * power_derate * 0.3
        else:
            severity = InsightSeverity.WARNING
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * power_derate * 0.1

        return InsightFinding(
            finding_id=str(uuid.uuid4())[:8],
            ts=ts,
            site_id=site_id,
            category=InsightCategory.POWER_CONSTRAINTS,
            severity=severity,
            title=f"Power Capacity Derated by {derate_pct:.0f}%",
            description=(
                f"Maximum power output is constrained to {min(sop_charge, sop_discharge)/1000:.1f}MW "
                f"(nominal: {max_power/1000:.1f}MW). This {derate_pct:.0f}% derating may be due to "
                f"SoC limits, temperature, or cell constraints."
            ),
            recommendation=(
                "Review constraint sources (SoC, temperature, cell health). If thermal, "
                "check HVAC operation. If SoC-related, adjust operating strategy. "
                "Consider maintenance if persistent."
            ),
            estimated_value_gbp=value_impact,
            confidence=0.8,
        )

    def _create_imbalance_finding(
        self,
        site_id: str,
        ts: datetime,
        imbalance_score: float,
    ) -> InsightFinding:
        """Create cell imbalance insight."""
        if imbalance_score > 60:
            severity = InsightSeverity.CRITICAL
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.08
        elif imbalance_score > 45:
            severity = InsightSeverity.ALERT
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.04
        else:
            severity = InsightSeverity.WARNING
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.02

        return InsightFinding(
            finding_id=str(uuid.uuid4())[:8],
            ts=ts,
            site_id=site_id,
            category=InsightCategory.CELL_IMBALANCE,
            severity=severity,
            title=f"Cell Imbalance Score: {imbalance_score:.0f}/100",
            description=(
                f"Rack-level imbalance score of {imbalance_score:.0f} indicates significant "
                f"variation between cells. This reduces usable capacity and accelerates degradation."
            ),
            recommendation=(
                "Schedule passive balancing cycle during low-demand period. Review cell-level "
                "data for outliers. Consider proactive maintenance if specific cells show "
                "consistent weakness."
            ),
            estimated_value_gbp=value_impact,
            confidence=0.75,
        )

    def _create_thermal_finding(
        self,
        site_id: str,
        ts: datetime,
        max_temp: float,
        avg_temp: float,
    ) -> InsightFinding:
        """Create thermal insight."""
        temp_delta = max_temp - avg_temp

        if max_temp > 45 or temp_delta > 8:
            severity = InsightSeverity.CRITICAL
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.1
        elif max_temp > 40 or temp_delta > 5:
            severity = InsightSeverity.ALERT
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.05
        else:
            severity = InsightSeverity.WARNING
            value_impact = self.site_capacity_mwh * self.revenue_per_mwh * 0.02

        return InsightFinding(
            finding_id=str(uuid.uuid4())[:8],
            ts=ts,
            site_id=site_id,
            category=InsightCategory.THERMAL,
            severity=severity,
            title=f"Thermal Alert: Max {max_temp:.1f}°C (Δ{temp_delta:.1f}°C)",
            description=(
                f"Maximum cell temperature of {max_temp:.1f}°C detected with {temp_delta:.1f}°C "
                f"variation from average. Elevated temperatures accelerate degradation and may "
                f"trigger protective derating."
            ),
            recommendation=(
                "Check HVAC system operation and setpoints. Review airflow distribution for "
                "hot spots. Consider reducing power during peak ambient temperature periods. "
                "Inspect thermal interface materials if issue persists."
            ),
            estimated_value_gbp=value_impact,
            confidence=0.9,
        )
