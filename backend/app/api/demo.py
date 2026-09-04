"""Demo data API endpoints for SHARMI Phase 1."""

from fastapi import APIRouter, HTTPException

from ..services.data_loader import get_data_loader

router = APIRouter(prefix="/demo", tags=["demo"])


def _get_dataset():
    """Get the loaded demo dataset."""
    return get_data_loader().get_dataset()


@router.get("/communities")
def list_communities() -> list[dict]:
    """Return all communities."""
    dataset = _get_dataset()
    return [c.model_dump() for c in dataset.communities]


@router.get("/communities/{community_id}")
def get_community(community_id: str) -> dict:
    """Return a single community by ID."""
    dataset = _get_dataset()
    for community in dataset.communities:
        if community.id == community_id:
            return community.model_dump()
    raise HTTPException(status_code=404, detail=f"Community {community_id} not found")


@router.get("/hazards")
def list_hazards() -> list[dict]:
    """Return all hazards."""
    dataset = _get_dataset()
    return [h.model_dump() for h in dataset.hazards]


@router.get("/infrastructure")
def list_infrastructure() -> list[dict]:
    """Return all infrastructure nodes."""
    dataset = _get_dataset()
    return [i.model_dump() for i in dataset.infrastructure]


@router.get("/dependencies")
def list_dependencies() -> list[dict]:
    """Return all dependency relationships."""
    dataset = _get_dataset()
    return [d.model_dump() for d in dataset.dependencies]


@router.get("/relocation/sites")
def list_relocation_sites() -> list[dict]:
    """Return all relocation sites."""
    dataset = _get_dataset()
    return [r.model_dump() for r in dataset.relocation_sites]