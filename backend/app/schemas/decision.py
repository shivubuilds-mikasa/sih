"""Pydantic schemas for SHARMI Phase 8b — Decision Service (Officer Override + Audit Log)."""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class OverrideDecision(str, Enum):
    """Possible override decisions by an officer."""
    ACCEPT = "ACCEPT"
    MODIFY = "MODIFY"
    REJECT = "REJECT"


class DecisionCategory(str, Enum):
    """Category of decision being made."""
    SHADOW_ZONE = "SHADOW_ZONE"
    ACTION_RECOMMENDATION = "ACTION_RECOMMENDATION"
    RELOCATION = "RELOCATION"
    CONFIDENCE = "CONFIDENCE"
    TIME_TO_IMPACT = "TIME_TO_IMPACT"


class OverrideRequest(BaseModel):
    """Request schema for officer override."""

    officer_id: Annotated[str, Field(description="Unique identifier for the officer")]
    officer_name: Annotated[str, Field(description="Officer's name")]
    hazard_id: Annotated[str, Field(description="Hazard ID (e.g., H001)")]
    community_id: Annotated[str, Field(description="Community ID (e.g., V001)")]
    category: Annotated[DecisionCategory, Field(description="Category of decision being overridden")]
    decision: Annotated[OverrideDecision, Field(description="Override decision: ACCEPT, MODIFY, or REJECT")]
    justification: Annotated[str, Field(min_length=1, description="Justification for the override decision")]
    modified_recommendation: Optional[Annotated[str, Field(description="Modified recommendation (required for MODIFY decision)")]] = None


class AuditEntry(BaseModel):
    """Audit log entry schema."""

    audit_id: str
    timestamp: str
    hazard_id: str
    hazard_type: str
    community_id: str
    community_name: str
    category: DecisionCategory
    officer_id: str
    officer_name: str
    decision: OverrideDecision
    original_recommendation: str
    final_recommendation: str
    justification: str
    zone_type: str
    risk_level: Optional[str] = None
    time_to_impact: Optional[float] = None
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None


class OverrideResponse(BaseModel):
    """Response schema for override submission."""

    audit_id: str
    final_recommendation: str
    decision: OverrideDecision
    timestamp: str
    note: str = (
        "This is a deterministic synthetic prototype for demonstration. "
        "Override decisions are logged for audit purposes only. "
        "Officer accountability is simulated."
    )


class AuditLogRequest(BaseModel):
    """Request schema for audit log query."""

    hazard_id: Optional[str] = None
    community_id: Optional[str] = None
    officer_id: Optional[str] = None
    category: Optional[DecisionCategory] = None
    decision: Optional[OverrideDecision] = None
    limit: Annotated[int, Field(ge=1, le=1000, default=100)] = 100
    offset: Annotated[int, Field(ge=0, default=0)] = 0


class AuditLogResponse(BaseModel):
    """Response schema for audit log query."""

    entries: list[AuditEntry]
    total: int
    limit: int
    offset: int


class AuditSummaryResponse(BaseModel):
    """Response schema for audit log summary."""

    total_entries: int
    by_decision: dict[str, int]
    by_category: dict[str, int]
    by_officer: dict[str, int]
    note: str = "This is a synthetic prototype audit log. Data is not persisted across restarts."