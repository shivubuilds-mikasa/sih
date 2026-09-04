"""Pydantic schemas for SHARMI Phase 3 — Cascade Engine API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class CascadeNode(BaseModel):
    """A node in the cascade path."""

    node_id: str
    node_type: Literal["hazard", "infrastructure", "community"]
    name: str


class CascadePath(BaseModel):
    """A single cascade path from hazard to affected node."""

    nodes: list[CascadeNode]
    propagation_strength: Annotated[float, Field(ge=0.0, le=1.0, description="Minimum dependency weight along the path")]


class AffectedService(BaseModel):
    """An affected service derived from infrastructure."""

    service_type: str
    infrastructure_id: str
    infrastructure_name: str


class CascadeSimulateRequest(BaseModel):
    """Request schema for cascade simulation."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to simulate cascade from (e.g., H001)")]


class CascadeSimulationResponse(BaseModel):
    """Response schema for cascade simulation."""

    hazard_id: str
    hazard_type: str
    affected: bool
    affected_node_ids: list[str]
    cascade_paths: list[CascadePath]
    affected_community_ids: list[str]
    affected_services: list[AffectedService]
    explanation: str
    note: str = (
        "This is a deterministic prototype cascade simulation. "
        "Dependency weights and the propagation threshold (0.70) are synthetic "
        "demonstration parameters, not calibrated real-world failure probabilities."
    )