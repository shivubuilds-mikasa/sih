# SHARMI — Development Phases

SHARMI is being built incrementally for the SIH prototype. Each phase produces working, testable output.

## Phase Overview

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Foundation | Project structure, backend scaffolding, configuration, tests |
| 1 | Demo Data & Domain Models | **COMPLETE** — Domain models, Shivapur synthetic dataset, data loader, read APIs |
| 2 | Direct Risk Engine | **COMPLETE** — Weighted formula, classification, explainable API, ranked endpoint |
| 3 | Infrastructure Cascade Engine | Dependency graph and cascade simulation |
| 4 | Cascade Shadow Zone | Identification of indirectly-affected zones |
| 5 | Time-to-Impact & Action Engine | Impact timing and explainable recommendations |
| 6 | Relocation Optimizer | Safe relocation route and destination planning |
| 7 | Relocation Sustainability Score | Long-term viability scoring for relocation plans |
| 8 | Confidence & Officer Override | Reliability indicators and officer decision layer |
| 9 | Unified Decision API | Single endpoint composing all engines |
| 10 | Frontend Dashboard | Visual interface for exploration and decision-making |
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

## Notes

- Each phase builds on the previous one but can be tested independently.
- Phases 0–8 are backend-focused. Phase 10 introduces the frontend.
- Phase 11 is focused on polish and demo readiness, not new features.
