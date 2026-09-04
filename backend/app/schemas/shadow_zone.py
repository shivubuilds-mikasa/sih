"""Pydantic schemas for SHARMI Phase 4 — Cascade Shadow Zone API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ZoneClassification(BaseModel):
    """Classification of a community's zone type."""

    community_id: str
    community_name: str
    zone_type: Literal["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]
    direct_hazard_exposure: bool
    cascade_affected: bool
    cascade_path: list[str] | None = Field(default=None, description="Path from hazard to community through cascade")
    explanation: str


class ShadowZoneAnalyzeRequest(BaseModel):
    """Request schema for shadow zone analysis."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to analyze (e.g., H001)")]


class ShadowZoneAnalyzeResponse(BaseModel):
    """Response schema for shadow zone analysis."""

    hazard_id: str
    hazard_type: str
    directly_affected: list[ZoneClassification]
    cascade_shadow: list[ZoneClassification]
    unaffected: list[ZoneClassification]
    explanation: str
    note: str = (
        "Shadow Zone means an area affected indirectly through dependency propagation "
        "in the prototype. It does not represent a scientifically validated hazard boundary. "
        "The cascade threshold (0.70) and dependency weights are synthetic demonstration parameters."
    )