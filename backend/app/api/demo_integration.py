"""Demo Integration API endpoints for SHARMI Phase 10.

Provides pre-configured demo scenarios and unified dashboard data
for the SIH demonstration.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Literal

from ..services.sharmi_engine import run_full_analysis, get_audit_log_summary
from ..services.data_loader import get_data_loader
from ..services.risk_engine import calculate_direct_risk
from ..services.cascade_engine import simulate_cascade
from ..services.shadow_zone_engine import analyze_shadow_zones
from ..services.time_to_impact import estimate_impact_timeline
from ..services.action_engine import generate_action_recommendations
from ..services.relocation_engine import optimize_relocation
from ..services.confidence_engine import evaluate_confidence
from ..services.decision_service import get_audit_log

router = APIRouter(prefix="/demo", tags=["demo-integration"])


@router.get("/scenarios")
def list_demo_scenarios() -> list[dict]:
    """Return available pre-configured demo scenarios."""
    return [
        {
            "id": "flood_h001",
            "name": "Flood H001 — Primary Demo Chain",
            "description": "H001 (flood) → R012 → P003 → V001 cascade with shadow zones V003, V005",
            "hazard_id": "H001",
            "key_communities": ["V001", "V002", "V003", "V004", "V005", "V006", "V009"],
            "expected_cascade": "H001 → R012 → P003 → V001",
            "shadow_zones": ["V003", "V005"],
        },
        {
            "id": "landslide_h002",
            "name": "Landslide H002 — Direct Only",
            "description": "H002 (landslide) with no infrastructure dependencies, directly affects V003, V005, V007",
            "hazard_id": "H002",
            "key_communities": ["V003", "V005", "V007"],
            "expected_cascade": "No infrastructure cascade (direct hazard only)",
            "shadow_zones": [],
        },
        {
            "id": "cyclone_h003",
            "name": "Cyclone H003 — All Direct",
            "description": "H003 (cyclone) directly affects all 10 communities, no shadow zones",
            "hazard_id": "H003",
            "key_communities": ["V001", "V002", "V003", "V004", "V005", "V006", "V007", "V008", "V009", "V010"],
            "expected_cascade": "All communities directly affected",
            "shadow_zones": [],
        },
        {
            "id": "heatwave_h004",
            "name": "Heatwave H004 — All Direct",
            "description": "H004 (heatwave) directly affects all 10 communities, no shadow zones",
            "hazard_id": "H004",
            "key_communities": ["V001", "V002", "V003", "V004", "V005", "V006", "V007", "V008", "V009", "V010"],
            "expected_cascade": "All communities directly affected",
            "shadow_zones": [],
        },
    ]


@router.get("/scenarios/{scenario_id}")
def get_demo_scenario(scenario_id: str) -> dict:
    """Get detailed demo scenario configuration."""
    scenarios = {s["id"]: s for s in list_demo_scenarios()}
    if scenario_id not in scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    return scenarios[scenario_id]


@router.post("/scenarios/{scenario_id}/run")
def run_demo_scenario(scenario_id: str, request: Request) -> dict:
    """Run complete SHARMI analysis for a demo scenario."""
    scenarios = {s["id"]: s for s in list_demo_scenarios()}
    if scenario_id not in scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

    hazard_id = scenarios[scenario_id]["hazard_id"]
    request_id = getattr(request.state, "request_id", "unknown")

    result = run_full_analysis(hazard_id)

    return {
        "scenario_id": scenario_id,
        "scenario_name": scenarios[scenario_id]["name"],
        "request_id": request_id,
        "analysis": result,
    }


@router.get("/dashboard/{hazard_id}")
def get_dashboard_data(hazard_id: str) -> dict:
    """Get unified dashboard data for a hazard — all engines in one response.

    This endpoint composes all Phase 1-9 engine outputs for frontend consumption.
    """
    # Validate hazard exists
    loader = get_data_loader()
    dataset = loader.get_dataset()
    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    if not hazard:
        raise HTTPException(status_code=404, detail=f"Hazard {hazard_id} not found")

    # Run all engines
    cascade_result = simulate_cascade(hazard_id)
    shadow_result = analyze_shadow_zones(hazard_id)
    timeline_result = estimate_impact_timeline(hazard_id)
    action_result = generate_action_recommendations(hazard_id)
    relocation_result = optimize_relocation(hazard_id)
    confidence_result = evaluate_confidence(hazard_id)
    audit_summary = get_audit_log_summary()

    # Build community lookup
    community_lookup = {c.id: c for c in dataset.communities}

    # Build dashboard community cards
    community_cards = []
    for community in dataset.communities:
        # Get zone classification
        zone_info = None
        for cls in shadow_result.directly_affected + shadow_result.cascade_shadow + shadow_result.unaffected:
            if cls.community_id == community.id:
                zone_info = cls
                break

        # Get timeline
        timeline_info = next((n for n in timeline_result.timeline if n.node_id == community.id and n.node_type == "community"), None)

        # Get action
        action_info = next((a for a in action_result.recommendations if a.community_id == community.id), None)

        # Get relocation
        relocation_info = next((p for p in relocation_result.plans if p.community_id == community.id), None)

        # Get confidence
        confidence_info = next((c for c in confidence_result.community_confidences if c.community_id == community.id), None)

        # Get risk
        exposure = 1.0 if community.id in hazard.affected_communities else 0.0
        risk_res = calculate_direct_risk(
            hazard_intensity=hazard.intensity,
            exposure=exposure,
            vulnerability=community.vulnerability,
        )

        community_cards.append({
            "community_id": community.id,
            "community_name": community.name,
            "population": community.population,
            "vulnerability": community.vulnerability,
            "coordinates": {"lat": community.latitude, "lon": community.longitude},
            "zone": zone_info.zone_type if zone_info else "UNKNOWN",
            "direct_hazard_exposure": community.id in hazard.affected_communities,
            "cascade_path": zone_info.cascade_path if zone_info else None,
            "risk_score": risk_res.risk_score,
            "risk_level": risk_res.risk_level,
            "time_to_impact": timeline_info.estimated_propagation_time if timeline_info else None,
            "action": action_info.action if action_info else "MONITOR",
            "action_confidence": action_info.confidence if action_info else 0.0,
            "action_rationale": action_info.rationale if action_info else "No analysis available",
            "affected_services": action_info.affected_services if action_info else [],
            "relocation_site": relocation_info.assigned_site_id if relocation_info else None,
            "relocation_urgency": (
                "CRITICAL" if relocation_info and relocation_info.urgency_score >= 0.8 else
                "HIGH" if relocation_info and relocation_info.urgency_score >= 0.6 else
                "MEDIUM" if relocation_info and relocation_info.urgency_score >= 0.4 else
                "LOW" if relocation_info and relocation_info.urgency_score > 0 else
                None
            ),
            "confidence_score": confidence_info.overall_confidence if confidence_info else 0.0,
            "confidence_level": confidence_info.confidence_level if confidence_info else "LOW",
        })

    return {
        "hazard": {
            "id": hazard.id,
            "type": hazard.type.value,
            "intensity": hazard.intensity,
            "probability": hazard.probability,
            "affected_communities": hazard.affected_communities,
        },
        "summary": {
            "total_communities": len(dataset.communities),
            "directly_affected": len(shadow_result.directly_affected),
            "cascade_shadow": len(shadow_result.cascade_shadow),
            "unaffected": len(shadow_result.unaffected),
            "total_population_at_risk": sum(
                c["population"] for c in community_cards
                if c["zone"] in ["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE"]
            ),
            "evacuation_recommended": sum(1 for c in community_cards if c["action"] == "EVACUATION_ASSESSMENT"),
            "protect": sum(1 for c in community_cards if c["action"] == "PROTECT"),
            "inspect": sum(1 for c in community_cards if c["action"] == "INSPECT"),
            "prepare": sum(1 for c in community_cards if c["action"] == "PREPARE"),
            "monitor": sum(1 for c in community_cards if c["action"] == "MONITOR"),
            "relocation_required": sum(1 for c in community_cards if c["relocation_site"] is not None),
        },
        "cascade_paths": [
            {
                "path_id": f"path_{i}",
                "nodes": [{"id": n.node_id, "type": n.node_type, "name": n.name} for n in path.nodes],
                "propagation_strength": path.propagation_strength,
            }
            for i, path in enumerate(cascade_result.cascade_paths)
        ],
        "timeline": [
            {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "name": n.name,
                "estimated_propagation_time": n.estimated_propagation_time,
                "predecessor": n.predecessor,
                "dependency_weight": n.dependency_weight,
            }
            for n in timeline_result.timeline
        ],
        "community_cards": community_cards,
        "relocation_sites": [
            {
                "site_id": s.site_id,
                "site_name": s.site_name,
                "capacity": s.capacity,
                "distance_km": s.distance_km,
                "composite_score": s.composite_score,
                "hazard_safety_score": s.hazard_safety_score,
                "livelihood_score": s.livelihood_score,
                "infrastructure_score": s.infrastructure_score,
                "school_access_score": s.school_access_score,
                "health_access_score": s.health_access_score,
                "distance_penalty": s.distance_penalty,
            }
            for s in relocation_result.site_scores
        ],
        "site_allocations": [
            {
                "site_id": sa.site_id,
                "site_name": sa.site_name,
                "capacity": sa.capacity,
                "allocated_population": sa.allocated_population,
                "remaining_capacity": sa.remaining_capacity,
                "communities": sa.communities,
                "utilization_pct": sa.utilization_pct,
            }
            for sa in relocation_result.site_allocations
        ],
        "audit_summary": audit_summary,
        "note": (
            "This is a deterministic synthetic prototype for SIH demonstration. "
            "All scores, classifications, and recommendations use synthetic models "
            "with prototype parameters. Results are for officer decision-support only "
            "and are NOT statistically calibrated. Do not use for real emergency decisions."
        ),
    }


@router.get("/dashboard")
def list_dashboard_hazards() -> list[dict]:
    """List available hazards for dashboard."""
    loader = get_data_loader()
    dataset = loader.get_dataset()
    return [
        {
            "id": h.id,
            "type": h.type.value,
            "intensity": h.intensity,
            "probability": h.probability,
            "affected_count": len(h.affected_communities),
        }
        for h in dataset.hazards
    ]


@router.get("/audit/recent")
def get_recent_audit(limit: int = 20) -> list[dict]:
    """Get recent audit log entries across all hazards."""
    entries = get_audit_log(limit=limit, offset=0)
    return [e.to_dict() for e in entries]


@router.get("/health/detailed")
def detailed_health() -> dict:
    """Detailed health check with engine status."""
    loader = get_data_loader()
    dataset = loader.get_dataset()

    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": "development",
        "data_loaded": True,
        "dataset": {
            "district": dataset.district.id,
            "communities": len(dataset.communities),
            "hazards": len(dataset.hazards),
            "infrastructure": len(dataset.infrastructure),
            "dependencies": len(dataset.dependencies),
            "relocation_sites": len(dataset.relocation_sites),
        },
        "engines": {
            "risk": "operational",
            "cascade": "operational",
            "shadow_zone": "operational",
            "time_to_impact": "operational",
            "action": "operational",
            "relocation": "operational",
            "confidence": "operational",
            "decision": "operational",
            "sharmi": "operational",
        },
        "note": "All engines operational - deterministic synthetic prototype for SIH demo.",
    }