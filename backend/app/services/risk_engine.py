"""SHARMI Phase 2 — Direct Risk Engine.

Transparent baseline direct-risk calculation using a weighted formula:
risk_score = 0.50 * hazard_intensity + 0.30 * exposure + 0.20 * vulnerability

All inputs normalized to [0, 1]. This is a prototype scoring model, not a
scientifically calibrated disaster-risk forecast.
"""

from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


# Weights are module-level constants for transparency and testability
WEIGHT_HAZARD_INTENSITY: float = 0.50
WEIGHT_EXPOSURE: float = 0.30
WEIGHT_VULNERABILITY: float = 0.20

# Classification thresholds
THRESHOLD_LOW_MAX: float = 0.29
THRESHOLD_MEDIUM_MAX: float = 0.59


def _validate_input(value: float, name: str) -> None:
    """Validate that a risk input is in [0, 1]."""
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def classify_risk(score: float) -> RiskLevel:
    """Classify a risk score into LOW/MEDIUM/HIGH."""
    if score <= THRESHOLD_LOW_MAX:
        return "LOW"
    if score <= THRESHOLD_MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def calculate_risk_score(
    hazard_intensity: float,
    exposure: float,
    vulnerability: float,
) -> float:
    """Calculate the direct risk score using the SHARMI baseline formula.

    Args:
        hazard_intensity: Normalized hazard intensity [0, 1]
        exposure: Normalized exposure [0, 1]
        vulnerability: Normalized community vulnerability [0, 1]

    Returns:
        Risk score in [0, 1]
    """
    _validate_input(hazard_intensity, "hazard_intensity")
    _validate_input(exposure, "exposure")
    _validate_input(vulnerability, "vulnerability")

    score = (
        WEIGHT_HAZARD_INTENSITY * hazard_intensity
        + WEIGHT_EXPOSURE * exposure
        + WEIGHT_VULNERABILITY * vulnerability
    )
    # Clamp to [0, 1] for floating-point safety
    return max(0.0, min(1.0, score))


def generate_explanation(
    hazard_intensity: float,
    exposure: float,
    vulnerability: float,
    risk_level: RiskLevel,
) -> str:
    """Generate a human-readable explanation of the risk calculation."""
    parts = []
    if hazard_intensity > 0.7:
        parts.append("high hazard intensity")
    elif hazard_intensity > 0.4:
        parts.append("moderate hazard intensity")
    else:
        parts.append("low hazard intensity")

    if exposure > 0.7:
        parts.append("high exposure")
    elif exposure > 0.4:
        parts.append("moderate exposure")
    else:
        parts.append("low exposure")

    if vulnerability > 0.7:
        parts.append("elevated community vulnerability")
    elif vulnerability > 0.4:
        parts.append("moderate community vulnerability")
    else:
        parts.append("low community vulnerability")

    base = f"Direct risk score is calculated from {', '.join(parts)} using the SHARMI baseline weighted model."
    return f"{base} Resulting level: {risk_level}."


@dataclass(frozen=True)
class RiskComponents:
    """Component values used in risk calculation."""
    hazard_intensity: float
    exposure: float
    vulnerability: float


@dataclass(frozen=True)
class RiskWeights:
    """Weights used in risk calculation."""
    hazard_intensity: float = WEIGHT_HAZARD_INTENSITY
    exposure: float = WEIGHT_EXPOSURE
    vulnerability: float = WEIGHT_VULNERABILITY


@dataclass(frozen=True)
class RiskResult:
    """Complete result of a direct risk calculation."""
    risk_score: float
    risk_level: RiskLevel
    components: RiskComponents
    weights: RiskWeights
    explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "risk_score": round(self.risk_score, 4),
            "risk_level": self.risk_level,
            "components": {
                "hazard_intensity": self.components.hazard_intensity,
                "exposure": self.components.exposure,
                "vulnerability": self.components.vulnerability,
            },
            "weights": {
                "hazard_intensity": self.weights.hazard_intensity,
                "exposure": self.weights.exposure,
                "vulnerability": self.weights.vulnerability,
            },
            "explanation": self.explanation,
        }


def calculate_direct_risk(
    hazard_intensity: float,
    exposure: float,
    vulnerability: float,
) -> RiskResult:
    """Main entry point for direct risk calculation.

    Args:
        hazard_intensity: Normalized hazard intensity [0, 1]
        exposure: Normalized exposure [0, 1]
        vulnerability: Normalized community vulnerability [0, 1]

    Returns:
        RiskResult with score, level, components, weights, and explanation
    """
    score = calculate_risk_score(hazard_intensity, exposure, vulnerability)
    level = classify_risk(score)
    components = RiskComponents(hazard_intensity, exposure, vulnerability)
    weights = RiskWeights()
    explanation = generate_explanation(hazard_intensity, exposure, vulnerability, level)

    return RiskResult(
        risk_score=score,
        risk_level=level,
        components=components,
        weights=weights,
        explanation=explanation,
    )