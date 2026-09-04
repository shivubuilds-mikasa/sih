# SHARMI — Development Phases

SHARMI is being built incrementally for the SIH prototype. Each phase produces working, testable output.

## Phase Overview

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Foundation | Project structure, backend scaffolding, configuration, tests |
| 1 | Demo Data & Domain Models | **COMPLETE** — Domain models, Shivapur synthetic dataset, data loader, read APIs |
| 2 | Direct Risk Engine | **COMPLETE** — Weighted formula, classification, explainable API, ranked endpoint |
| 3 | Infrastructure Cascade Engine | **COMPLETE** — NetworkX graph, threshold propagation, explainable cascade paths |
| 4 | Cascade Shadow Zone | **COMPLETE** — DIRECT/CASCADE_SHADOW/UNAFFECTED classification, explainable paths |
| 5 | Time-to-Impact & Action Engine | **COMPLETE** — Impact timing + explainable recommendations |
| 6 | Action Recommendation Engine | **COMPLETE** — Explainable prototype recommendations (MONITOR/PREPARE/INSPECT/PROTECT/EVACUATION_ASSESSMENT) |
| 7 | Relocation Optimizer | **COMPLETE** — Safe relocation route/destination planning with capacity, safety scores, urgency allocation |
| 7 | Relocation Sustainability Score | Long-term viability scoring for relocation plans |
| 8a | Confidence Engine | **COMPLETE** — 5-component scoring (data quality, model coverage, input completeness, cascade strength, time certainty) |
| 8b | Decision Service | **COMPLETE** — Officer override layer with audit logging (ACCEPT/REJECT/MODIFY) |
| 9 | Unified SHARMI Engine | **COMPLETE** — Single API composing all engines with decision override integration |
| 10 | API Hardening + Demo Integration | **COMPLETE** — Middleware stack (RequestID, Logging, RateLimit, CORS), demo scenarios, unified dashboard, health endpoints |
| 11 | SIH Demo Hardening | Performance, polish, demo scenarios, stress testing |

## Key Differentiators

The following capabilities are what set SHARMI apart from standard hazard maps:

- **Cascade Shadow Zone Detection** — Finding danger zones created indirectly by infrastructure failure chains
- **Safe Relocation Optimization** — Computing viable relocation plans that account for capacity, distance, and sustainability
- **Explainable Cascade Paths** — Tracing exactly why a zone is flagged as dangerous, through every link in the failure chain

## Phase 1 Deliverables

### Domain Models (`backend/app/models/domain.py`)
- **Community** — id, name, population (>0), vulnerability [0,1], lat [-90,90], lon [-180,180]
- **Hazard** — id, type (flood/landslide/cyclone/heatwave), intensity [0,1], probability [0,1], affected_communities[]
- **InfrastructureNode** — id, name, type (road/bridge/pump/hospital/school/power_substation/water_supply), failure_probability [0,1], serves[]
- **Dependency** — source, target, weight [0,1]
- **RelocationSite** — id, name, capacity (>0), distance_km (>=0), hazard/livelihood/infrastructure/school/health scores [0,1]
- **District** — id, name, description
- **DemoDataset** — Container for all entities

### Demo Dataset (`data/demo_data.json`)
- **District**: Shivapur (D001) — synthetic, documented as demo data
- **10 Communities**: V001–V010, varied populations (600–2100), vulnerabilities (0.42–0.81)
- **4 Hazards**: H001 (flood), H002 (landslide), H003 (cyclone), H004 (heatwave)
- **15 Infrastructure Nodes**: 2 roads, 2 bridges, 3 pumps, 2 hospitals, 3 schools, 2 power substations, 1 water supply
- **23 Dependencies**: Including critical chain H001→R012→P003→V001 for Phase 3 cascade demo
- **4 Relocation Sites**: RS01 (high hazard), RS02 (safe/good), RS03 (moderate), RS04 (very safe but far/poor access)

### Data Loading (`backend/app/services/data_loader.py`)
- `DataLoader` class with `load()`, `get_dataset()`, `reload()`
- Validates JSON against Pydantic models
- Locates data file relative to project root
- Module-level singleton accessor

### API Endpoints (`backend/app/api/demo.py`)
- GET `/demo/communities` — all communities
- GET `/demo/communities/{id}` — single community (404 if missing)
- GET `/demo/hazards` — all hazards
- GET `/demo/infrastructure` — all infrastructure nodes
- GET `/demo/dependencies` — all dependencies
- GET `/demo/relocation/sites` — all relocation sites

### Tests (`backend/tests/test_phase1.py`)
- 22 tests total (3 Phase 0 + 19 Phase 1)
- Data loading validation
- All entity validation
- Referential integrity (community IDs, infrastructure IDs)
- Critical demo chain verification (H001→R012→P003→V001)
- Relocation site profile distinctness
- All API endpoints + 404 behavior
- Backward compatibility with `/health`

## Phase 2 Deliverables

### Risk Engine (`backend/app/services/risk_engine.py`)
- **Core functions**: `calculate_risk_score()`, `classify_risk()`, `calculate_direct_risk()`
- **Pure, testable functions** with input validation
- **Constants**: weights (0.50, 0.30, 0.20), thresholds (0.29, 0.59)
- **Explanation generator** — natural-language summary based on actual component values

### Risk Schemas (`backend/app/schemas/risk.py`)
- `RiskCalculateRequest` — hazard_intensity, exposure, vulnerability (all [0,1])
- `RiskCalculateResponse` — risk_score, risk_level, components, weights, explanation
- `RankedCommunityRisk` — community_id, community_name, risk_score, risk_level
- `RankedRiskResponse` — hazard metadata, exposure rule, communities[], note

### Risk API (`backend/app/api/risk.py`)
- `POST /risk/calculate` — Direct calculation from explicit inputs
- `GET /risk/ranked` — Ranked communities using H001 (flood) with prototype exposure rule

### Prototype Exposure Rule
```
exposure = 1.0 if community.id in H001.affected_communities else 0.0
```
**Documented limitation:** This is a deterministic synthetic rule for the demo, not a realistic geospatial model.

### Tests (`backend/tests/test_phase2.py`)
- 25 tests (13 core engine, 12 API)
- Known calculation verification (0.50×0.8 + 0.30×0.6 + 0.20×0.7 = 0.72)
- Boundary tests: 0.00→LOW, 0.29→LOW, 0.30→MEDIUM, 0.59→MEDIUM, 0.60→HIGH, 1.00→HIGH
- All-zero (0.0→LOW), all-one (1.0→HIGH)
- Input validation (rejects >1, <0, non-numeric)
- API success, validation errors
- Ranked endpoint: returns communities, sorted descending, V001 exposed, non-exposed lower
- Metadata in response (hazard_id, exposure_rule, note)
- Backward compatibility with Phase 0 & 1 endpoints

## Phase 4 Deliverables

### Shadow Zone Engine (`backend/app/services/shadow_zone_engine.py`)
- **Core function**: `analyze_shadow_zones(hazard_id)` — returns complete zone classification
- **Classification types**: DIRECT_HAZARD_ZONE, CASCADE_SHADOW_ZONE, UNAFFECTED
- **Pure, testable functions** with input validation
- **Traceable paths**: Each shadow zone includes the cascade path from hazard to community
- **Explanation generator** — natural-language summary for each classification

### Shadow Zone Schemas (`backend/app/schemas/shadow_zone.py`)
- `ShadowZoneAnalyzeRequest` — hazard_id
- `ShadowZoneAnalyzeResponse` — hazard metadata, directly_affected[], cascade_shadow[], unaffected[], explanation, note
- `ZoneClassification` — community_id, community_name, zone_type, direct_hazard_exposure, cascade_affected, cascade_path, explanation

### Shadow Zone API (`backend/app/api/shadow_zone.py`)
- `POST /shadow-zone/analyze` — Analyze shadow zones for a hazard

### Tests (`backend/tests/test_phase4.py`)
- 24 tests total (12 core engine, 9 API, 3 backward compatibility)
- V001–V009 direct zone classification for H001
- Shadow zone detection logic
- H003/H004 have no shadow zones (all communities directly affected)
- Deterministic output verification
- Unknown hazard → 404
- All previous tests still pass (96 total)

### Prototype Limitation Note
"Shadow Zone means an area affected indirectly through dependency propagation in the prototype. It does not represent a scientifically validated hazard boundary."

## Phase 8a Deliverables — Confidence Engine

### Confidence Engine (`backend/app/services/confidence_engine.py`)
- **Core function**: `evaluate_confidence(hazard_id)` — returns per-community confidence scores
- **5-Component Scoring Model** with explicit weights:
  - Data Quality (25%) — Completeness of community/hazard/infrastructure data
  - Model Coverage (25%) — Engine coverage for the hazard type
  - Input Completeness (20%) — Required inputs present for all communities
  - Cascade Strength (20%) — Average propagation strength along cascade paths
  - Time Certainty (10%) — Consistency of time-to-impact estimates
- **Classification Thresholds**: LOW (0.00-0.39), MEDIUM (0.40-0.69), HIGH (0.70-1.00)
- Pure, testable functions with deterministic output
- Explicit prototype limitation note: NOT statistical confidence intervals

### Confidence Schemas (`backend/app/schemas/confidence.py`)
- `ConfidenceComponents` — individual component scores with metadata
- `CommunityConfidence` — community_id, overall_confidence, confidence_level, components[], explanation
- `ConfidenceRequest` / `ConfidenceResponse` — API models

### Confidence API (`backend/app/api/confidence.py`)
- `POST /confidence/evaluate` — Evaluate confidence for all communities for a hazard

### Tests (`backend/tests/test_phase8a.py`)
- 31 tests total (15 core engine, 12 API, 4 backward compatibility)
- Component weight verification, threshold boundary tests
- Per-community confidence with full breakdown
- Deterministic output verification
- Unknown hazard → 404
- All previous tests still pass

## Phase 8b Deliverables — Decision Service

### Decision Service (`backend/app/services/decision_service.py`)
- **Core functions**: `submit_override()`, `get_audit_log()`, `get_audit_summary()`, `clear_audit_log()`
- **Override Categories**: ACTION_RECOMMENDATION, RELOCATION_PLAN, EVACUATION_ORDER, RESOURCE_ALLOCATION, SHADOW_ZONE
- **Decision Options**: ACCEPT, REJECT, MODIFY
- **Audit Logging**: All overrides logged with officer ID/name, timestamp, hazard, community, category, decision, justification (min 10 chars), original vs final recommendation, context (zone_type, risk_level, time_to_impact, confidence_score)
- In-memory audit log (prototype, replace with persistent storage for production)

### Decision Schemas (`backend/app/schemas/decision.py`)
- `OverrideDecision` enum (ACCEPT/REJECT/MODIFY)
- `DecisionCategory` enum
- `DecisionOverrideRequest` — officer_id, officer_name, hazard_id, community_id, category, decision, justification, modified_recommendation (optional for MODIFY)
- `AuditEntry` — Full audit log entry with all context
- `DecisionOverrideResponse` / `AuditLogResponse` / `AuditSummaryResponse` — API models

### Decision API (`backend/app/api/decision.py`)
- `POST /decisions/override` — Submit decision override
- `POST /decisions/audit` — Query audit log (with filters)
- `GET /decisions/audit/summary` — Audit statistics

### Tests (`backend/tests/test_phase8b.py`)
- 42 tests total (18 core service, 18 API, 6 backward compatibility)
- Override decision logic (ACCEPT/REJECT/MODIFY)
- Audit log persistence and querying
- Validation (justification required, min length)
- Enum serialization
- All previous tests still pass

## Phase 9 Deliverables — Unified SHARMI Engine

### SHARMI Engine (`backend/app/services/sharmi_engine.py`)
- **Core function**: `run_full_analysis(hazard_id)` — runs all 7 engines in sequence
- **Composed Analysis** returns:
  - Direct risk scores for all communities
  - Cascade simulation results
  - Shadow zone classifications
  - Time-to-impact timeline
  - Action recommendations
  - Relocation plans
  - Confidence scores
  - Any applicable officer overrides (from audit log)
- **Decision Integration**:
  - `submit_decision_override()` — Submit override within analysis context
  - `get_decision_audit()` — Query audit log for hazard
- Deterministic, fully traceable output with prototype limitation note

### SHARMI Schemas (`backend/app/schemas/sharmi.py`)
- `CommunityAnalysis` — Complete per-community analysis (risk, zone, timeline, action, relocation, confidence, override)
- `SHARMIAnalysisResult` — Full analysis result with summary, community_analyses[], cascade_paths_summary[], relocation_sites_summary[], overall_explanation
- `SHARMIAnalyzeRequest` / `SHARMIAnalyzeResponse` / `SHARMIOverrideRequest` / `SHARMIAuditResponse` / `SHARMIAuditSummaryResponse`

### SHARMI API (`backend/app/api/sharmi.py`)
- `POST /sharmi/analyze` — Run complete SHARMI analysis
- `POST /sharmi/override` — Submit decision override
- `POST /sharmi/audit` — Query audit log for hazard
- `GET /sharmi/audit/summary` — Audit statistics

### Tests (`backend/tests/test_phase9.py`)
- 40 tests total (15 core engine, 20 API, 5 backward compatibility)
- Full analysis with all engines
- Decision override integration
- Audit log querying
- Setup method clears audit log between tests
- All previous tests still pass (270+ total)

## Phase 10 Deliverables — API Hardening + Demo Integration

### Middleware Stack (`backend/app/middleware/`)
1. **RequestIDMiddleware** (`request_id.py`) — Generates/propagates X-Request-ID for tracing
2. **LoggingMiddleware** (`logging.py`) — Structured JSON logging (request_start, request_complete, request_error)
3. **RateLimitMiddleware** (`rate_limit.py`) — In-memory rate limiting (120/min, 1000/hr), test client excluded via user-agent detection
4. **CORS** — Allow all origins for demo (configure for production)

### Demo Integration API (`backend/app/api/demo_integration.py`)
- `GET /demo/scenarios` — List 4 pre-configured scenarios (flood_h001, landslide_h002, cyclone_h003, heatwave_h004)
- `GET /demo/scenarios/{id}` — Scenario details with key communities, expected cascade, shadow zones
- `POST /demo/scenarios/{id}/run` — Run full SHARMI analysis for scenario
- `GET /demo/dashboard/{hazard_id}` — Unified dashboard (all engines in one response: hazard, summary, cascade_paths, timeline, community_cards, relocation_sites, site_allocations, audit_summary)
- `GET /demo/dashboard` — List available dashboard hazards
- `GET /demo/audit/recent` — Recent audit entries with limit parameter
- `GET /demo/health/detailed` — Engine status + dataset metadata (district, counts, engines)

### Tests (`backend/tests/test_phase10.py`)
- 25 tests total (4 scenarios, 3 dashboard, 2 audit, 1 health, 3 middleware, 1 CORS, 11 backward compatibility)
- All demo endpoints functional
- Middleware headers present (X-Request-ID, rate limit)
- Backward compatibility with all Phase 1-9 endpoints
- All 334 tests pass across all phases

## Notes

- Each phase builds on the previous one but can be tested independently.
- Phases 0–10 are backend-focused. Frontend dashboard planned for future phase.
- Phase 11 is focused on polish and demo readiness, not new features.
