"""Domain models for SHARMI Phase 1 — Demo data entities."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class HazardType(str, Enum):
    """Supported hazard types for Phase 1."""

    FLOOD = "flood"
    LANDSLIDE = "landslide"
    CYCLONE = "cyclone"
    HEATWAVE = "heatwave"


class InfrastructureType(str, Enum):
    """Supported infrastructure types for Phase 1."""

    ROAD = "road"
    BRIDGE = "bridge"
    PUMP = "pump"
    HOSPITAL = "hospital"
    SCHOOL = "school"
    POWER_SUBSTATION = "power_substation"
    WATER_SUPPLY = "water_supply"


class Community(BaseModel):
    """A residential community in the district."""

    id: str
    name: str
    population: Annotated[int, Field(gt=0)]
    vulnerability: Annotated[float, Field(ge=0.0, le=1.0)]
    latitude: Annotated[float, Field(ge=-90.0, le=90.0)]
    longitude: Annotated[float, Field(ge=-180.0, le=180.0)]


class Hazard(BaseModel):
    """A hazard affecting one or more communities."""

    id: str
    type: HazardType
    intensity: Annotated[float, Field(ge=0.0, le=1.0)]
    probability: Annotated[float, Field(ge=0.0, le=1.0)]
    affected_communities: list[str]


class InfrastructureNode(BaseModel):
    """An infrastructure node serving communities."""

    id: str
    name: str
    type: InfrastructureType
    failure_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    serves: list[str]


class Dependency(BaseModel):
    """A dependency relationship between infrastructure nodes."""

    source: str
    target: str
    weight: Annotated[float, Field(ge=0.0, le=1.0)]


class RelocationSite(BaseModel):
    """A candidate relocation site for displaced populations."""

    id: str
    name: str
    capacity: Annotated[int, Field(gt=0)]
    distance_km: Annotated[float, Field(ge=0.0)]
    hazard_score: Annotated[float, Field(ge=0.0, le=1.0)]
    livelihood_score: Annotated[float, Field(ge=0.0, le=1.0)]
    infrastructure_score: Annotated[float, Field(ge=0.0, le=1.0)]
    school_access: Annotated[float, Field(ge=0.0, le=1.0)]
    health_access: Annotated[float, Field(ge=0.0, le=1.0)]


class District(BaseModel):
    """District metadata."""

    id: str
    name: str
    description: str


class DemoDataset(BaseModel):
    """Complete demo dataset for Shivapur district."""

    district: District
    communities: list[Community]
    hazards: list[Hazard]
    infrastructure: list[InfrastructureNode]
    dependencies: list[Dependency]
    relocation_sites: list[RelocationSite]