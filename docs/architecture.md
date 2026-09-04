# SHARMI — Architecture

## Overview

SHARMI is designed as a modular, service-oriented decision-support system for disaster management. The architecture separates concerns into distinct engines that compose into a unified pipeline.

## Planned Components

### FastAPI API Layer

The HTTP interface for the system. Exposes REST endpoints for data ingestion, analysis requests, officer decisions, and audit queries.

**Status:** Phase 0 foundation in place. Phase 1 adds `/demo/*` read endpoints.

### Domain Models (Phase 1)

Core data entities that form the foundation for all engines:

**Community** — Residential populations with vulnerability scores and geographic coordinates.
**Hazard** — Hazard events (flood, landslide, cyclone, heatwave) with intensity, probability, and affected communities.
**InfrastructureNode** — Roads, bridges, pumps, hospitals, schools, power substations, water supply with failure probabilities and service areas.
**Dependency** — Generic weighted relationships between infrastructure nodes (and to communities) forming the cascade graph.
**RelocationSite** — Candidate sites with capacity, distance, and normalized scores for hazard, livelihood, infrastructure, school/health access.
**District** — Metadata container for the synthetic Shivapur district.

These models are defined in `backend/app/models/domain.py` and validated against `data/demo_data.json`.

### Risk Engine

Evaluates direct hazard exposure for geographic zones. Takes hazard intensity, exposure, and vulnerability as input; outputs direct risk scores with classification and explanation.

**Status:** **Complete — Phase 2**

#### Formula

```
risk_score = 0.50 × hazard_intensity + 0.30 × exposure + 0.20 × vulnerability
```

All inputs normalized to [0, 1].

#### Classification Thresholds

| Level | Range |
|-------|-------|
| LOW | 0.00 – 0.29 |
| MEDIUM | 0.30 – 0.59 |
| HIGH | 0.60 – 1.00 |

#### Exposure Model (Prototype)

Phase 2 uses a deterministic synthetic rule for exposure:
- If community is listed in the primary hazard's `affected_communities` → exposure = 1.0
- Otherwise → exposure = 0.0

This is a prototype rule for the SIH demo, **not** a realistic geospatial exposure model. Real exposure modeling requires flood extent mapping, elevation data, and hydraulic modeling — planned for later phases.

#### API Endpoints

- `POST /risk/calculate` — Calculate risk from explicit inputs
- `GET /risk/ranked` — Communities ranked by risk from primary demo hazard (H001)

#### Output Structure

Every calculation returns:
- `risk_score` — weighted score in [0, 1]
- `risk_level` — LOW/MEDIUM/HIGH
- `components` — the three input values
- `weights` — the three weights used
- `explanation` — natural-language summary referencing actual input values

### Cascade Engine

Models infrastructure dependencies and simulates how failure in one system triggers downstream failures. Builds a directed dependency graph using NetworkX and propagates disruption events through threshold-based rules.

**Status:** **Complete — Phase 3**

#### Graph Construction

- **Directed Graph** — Nodes represent entities (hazards, infrastructure, communities), edges represent dependencies
- **Node ID Collision Handling** — When infrastructure and hazard share an ID (e.g., H001), infrastructure nodes are prefixed with `INFRA_`
- **Dependency Weights** — Each edge carries a weight [0, 1] from the demo dataset

#### Propagation Rule

Deterministic threshold-based propagation:

```
cascade propagates when dependency.weight >= CASCADE_THRESHOLD (0.70)
```

This is a prototype rule for demonstrating dependency propagation. It is not a calibrated failure probability.

#### Critical Demo Chain

The engine correctly detects:

```
Flood H001
↓ (weight: 0.85)
Road 12 (R012)
↓ (weight: 0.78)
Pump 3 (P003)
↓ (weight: 0.88)
Village A (V001)
```

#### Output

- All affected node IDs (ordered, deterministic)
- Cascade path(s) with node metadata
- Affected community IDs
- Affected service types (water_supply, healthcare, education, power, access)
- Human-readable explanation
- Propagation strength (minimum weight along path)

#### API Endpoints

- `POST /cascade/simulate` — Run cascade simulation from a specified hazard

### Cascade Shadow Zone Identification

Identifies zones that are not directly hit by a hazard but are rendered dangerous by cascading infrastructure failures. This is SHARMI's primary differentiator.

**Status:** **Complete — Phase 4**

### Cascade Shadow Zone Identification

Identifies zones that are not directly hit by a hazard but are rendered dangerous by cascading infrastructure failures. This is SHARMI's primary differentiator.

**Status:** **Complete — Phase 4**

#### Classification

Every community is classified into one of three zones:

- **DIRECT_HAZARD_ZONE** — Community directly listed in the hazard's `affected_communities`
- **CASCADE_SHADOW_ZONE** — Community NOT directly affected but reached through infrastructure cascade propagation (dependency weight ≥ 0.70)
- **UNAFFECTED** — Community neither directly exposed nor cascade-reached

#### Implementation

- Service: `backend/app/services/shadow_zone_engine.py`
- API: `POST /shadow-zone/analyze`
- Uses existing cascade engine results
- Deterministic, explainable classification with full path traceability

#### Output

- Complete zone classification for all communities
- Cascade paths for shadow zone communities
- Human-readable explanation
- Explicit prototype limitation note

### Time-to-Impact Estimation

Estimates how long before a cascade-affected zone becomes critical, enabling prioritized response.

**Status:** **Complete — Phase 5**

#### Approach

Introduces a transparent prototype model for the order/timing of cascade impacts. It is a deterministic synthetic model, NOT a real-world timing prediction. The core rule:

```
estimated_propagation_time = BASE_DELAY * (1 - dependency_weight)
```

where `BASE_DELAY = 100` arbitrary units. Higher dependency weight → shorter propagation delay (stronger dependency = faster failure transmission). The output unit is abstract time units — not minutes/hours/days.

#### Implementation

- Service: `backend/app/services/time_to_impact.py`
- Iterative BFS collects cascade edges in propagation order (visited-set prevents cycle back-edges)
- Cumulative time accumulated along the critical path `H001 → R012 → P003 → V001`
- API: `POST /impact/timeline`
- Deterministic, explainable output with an explicit prototype limitation note

### Action Recommendation Engine

Generates explainable, actionable prototype recommendations for each identified risk zone, drawing on zone classification, direct risk, cascade impact, time-to-impact, and affected services. Does NOT make autonomous emergency decisions — provides decision-support for officer review.

**Status:** **Complete — Phase 6**

#### Action Categories

- **MONITOR** — Low risk, continue observation
- **PREPARE** — Moderate risk, ready resources and contingency plans
- **INSPECT** — Verify infrastructure/service status
- **PROTECT** — High risk, implement protective measures for population/assets
- **EVACUATION_ASSESSMENT** — Critical risk, assess evacuation feasibility (NOT an evacuation order)

#### Implementation

- Service: `backend/app/services/action_engine.py`
- API: `POST /actions/recommend`
- Combines: shadow zone classification, direct risk level, time-to-impact, affected services
- Deterministic, explainable recommendations with synthetic confidence scores
- Explicit prototype limitation note: NOT autonomous emergency orders

### Relocation Optimization Engine

Optimizes safe relocation routes and destinations for affected populations. Considers:
- Relocation site capacity and safety scores (hazard, livelihood, infrastructure, school, health)
- Distance from hazard zone
- Community zone classification and action urgency
- Population sizes and site utilization

**Status:** **Complete — Phase 7**

#### Weighted Scoring Model

Composite site score uses synthetic prototype weights:
- Hazard safety (inverse of hazard_score): 35%
- Livelihood: 20%
- Infrastructure: 20%
- School access: 15%
- Health access: 10%
- Distance penalty: 2% per km (linear, capped at 1.0)

#### Allocation Algorithm

Greedy allocation by urgency (zone priority × action urgency):
1. Sort communities by urgency descending
2. Assign each to best available site with capacity
3. Track site utilization and unallocated population

#### Implementation

- Service: `backend/app/services/relocation_engine.py`
- API: `POST /relocation/optimize`
- Deterministic, explainable output with prototype limitation note

### Confidence Engine

Quantifies the reliability of each recommendation based on data quality, model coverage, input completeness, cascade strength, and time certainty.

**Status:** **Complete — Phase 8a**

#### 5-Component Scoring Model

Composite confidence score with explicit weights:
- **Data Quality (25%)** — Completeness of community/hazard/infrastructure data
- **Model Coverage (25%)** — Engine coverage for the hazard type
- **Input Completeness (20%)** — Required inputs present for all communities
- **Cascade Strength (20%)** — Average propagation strength along cascade paths
- **Time Certainty (10%)** — Consistency of time-to-impact estimates

#### Classification Thresholds

| Level | Range |
|-------|-------|
| LOW | 0.00 – 0.39 |
| MEDIUM | 0.40 – 0.69 |
| HIGH | 0.70 – 1.00 |

#### Implementation

- Service: `backend/app/services/confidence_engine.py`
- API: `POST /confidence/evaluate`
- Per-community confidence with component breakdown
- Explicit prototype limitation note: NOT statistical confidence intervals

### Decision Service (Officer Override + Audit)

Provides override capability for field officers and logs all decisions for accountability.

**Status:** **Complete — Phase 8b**

#### Override Categories

- **ACTION_RECOMMENDATION** — Accept/reject/modify action recommendations
- **RELOCATION_PLAN** — Accept/reject/modify relocation allocations
- **EVACUATION_ORDER** — Accept/reject/modify evacuation decisions
- **RESOURCE_ALLOCATION** — Accept/reject/modify resource deployment

#### Decision Options

- **ACCEPT** — Endorse automated recommendation
- **REJECT** — Override with manual decision
- **MODIFY** — Adjust parameters with justification

#### Audit Logging

All overrides logged with:
- Officer ID, name, timestamp
- Hazard, community, category, decision
- Justification (required, min 10 chars)
- Previous recommendation vs. new decision

#### Implementation

- Service: `backend/app/services/decision_service.py`
- API: `POST /decisions/override`, `POST /decisions/audit`, `GET /decisions/audit/summary`
- In-memory audit log (prototype, replace with persistent storage for production)

### Unified SHARMI Engine

Single analysis endpoint composing all engines with decision override integration.

**Status:** **Complete — Phase 9**

#### Composed Analysis

Single call runs all engines and returns:
- Direct risk scores for all communities
- Cascade simulation results
- Shadow zone classifications
- Time-to-impact timeline
- Action recommendations
- Relocation plans
- Confidence scores
- Any applicable officer overrides (from audit log)

#### Decision Integration

- `POST /sharmi/override` — Submit override within analysis context
- `POST /sharmi/audit` — Query audit log for hazard
- `GET /sharmi/audit/summary` — Audit statistics

#### Implementation

- Service: `backend/app/services/sharmi_engine.py`
- API: `POST /sharmi/analyze`
- Deterministic, fully traceable output

### API Hardening + Demo Integration

Production-ready middleware and pre-configured demo scenarios.

**Status:** **Complete — Phase 10**

#### Middleware Stack

1. **RequestIDMiddleware** — Generates/propagates X-Request-ID for tracing
2. **LoggingMiddleware** — Structured JSON logging (request start, complete, error)
3. **RateLimitMiddleware** — In-memory rate limiting (120/min, 1000/hr), test client excluded
4. **CORS** — Allow all origins for demo

#### Demo Integration Endpoints

- `GET /demo/scenarios` — List 4 pre-configured scenarios
- `GET /demo/scenarios/{id}` — Scenario details
- `POST /demo/scenarios/{id}/run` — Run full analysis
- `GET /demo/dashboard/{hazard_id}` — Unified dashboard (all engines)
- `GET /demo/dashboard` — List available dashboard hazards
- `GET /demo/audit/recent` — Recent audit entries
- `GET /demo/health/detailed` — Engine status + dataset metadata

### Frontend Dashboard

Visual interface for viewing risk maps, cascade simulations, recommendations, and relocation plans.

**Status:** Planned — Future phase.

## Conceptual Data Flow

```
Hazard Event
    ↓
Direct Risk Assessment
    ↓
Infrastructure Dependency Mapping
    ↓
Cascade Simulation
    ↓
Cascade Shadow Zone Identification
    ↓
Time-to-Impact Estimation
    ↓
Action Recommendation Generation
    ↓
Relocation Optimization
    ↓
Officer Review & Decision
    ↓
Audit Log
```

Each stage feeds the next. The system is designed so components can be developed and tested independently before integration.

## Domain Model Relationships

```
Community
  ↑
  |  serves / affected_by
  |
InfrastructureNode ←→ Dependency ←→ InfrastructureNode
  ↑
  |  depends_on / powers
  |
Hazard

Affected Community
  ↓
Candidate Relocation Sites
```

- **Communities** are served by **InfrastructureNodes** and affected by **Hazards**
- **InfrastructureNodes** depend on each other via **Dependencies** (directed, weighted)
- **Hazards** trigger cascades through the dependency graph
- **RelocationSites** are candidate destinations for affected communities

## Design Principles

1. **Modularity** — Each engine is a self-contained service with clear inputs/outputs.
2. **Incremental buildability** — The system is useful at every phase, not just at the end.
3. **Explainability** — Every recommendation traces back to the data and reasoning that produced it.
4. **Offline-capable** — Core analysis works without live sensor feeds (uses historical/demo data).
5. **Human-in-the-loop** — Officers can override any automated recommendation with justification.
