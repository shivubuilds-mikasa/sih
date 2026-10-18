# SHARMI

**Smart Hazard Assessment & Relocation Management Intelligence**

> Seeing danger before it becomes disaster.

## What is SHARMI?

SHARMI is a disaster-management decision-support system designed to address the critical problem of **Hazard-based Red Zone Identification & Relocation Planning**.

At its core, SHARMI will enable:

- Identifying areas at risk from cascading infrastructure failures
- Simulating how one hazard event triggers downstream impacts
- Recommending actionable steps before disaster strikes
- Optimizing safe, sustainable relocation plans for affected populations

## Current Status

**Phase 10 — API Hardening + Demo Integration (Complete)**

This repository is being built incrementally. Phase 0 established the project foundation. Phase 1 introduced domain models and the Shivapur demo dataset. Phase 2 implements direct risk calculation. Phase 3 adds the Infrastructure Cascade Engine. Phase 4 adds Cascade Shadow Zone Identification. Phase 5 adds Time-to-Impact Estimation. Phase 6 adds Action Recommendation Engine. Phase 7 adds Relocation Optimizer. Phase 8a adds Confidence Engine. Phase 8b adds Decision Service. Phase 9 adds Unified SHARMI Engine. Phase 10 adds API hardening and demo integration:

- **Infrastructure Cascade Engine** — NetworkX-based dependency graph simulation
- **Threshold-based Propagation** — Deterministic rule: cascade propagates when dependency weight ≥ 0.70
- **Explainable Cascade Paths** — Full chain visualization from hazard to affected communities
- **Demo Chain Detection** — `H001 (flood) → R012 (Road 12) → P003 (Pump 3) → V001 (Village A)`
- **Affected Services** — Identifies impacted infrastructure and service types
- **Cascade Shadow Zone Identification** — Classifies communities as DIRECT_HAZARD_ZONE, CASCADE_SHADOW_ZONE, or UNAFFECTED based on direct hazard exposure vs. cascade propagation
- **Time-to-Impact Estimation** — Synthetic propagation timeline using BASE_DELAY * (1 - weight) formula
- **Action Recommendation Engine** — Explainable prototype recommendations (MONITOR, PREPARE, INSPECT, PROTECT, EVACUATION_ASSESSMENT) based on zone classification, direct risk, cascade impact, time-to-impact, affected services
- **Relocation Optimizer** — Safe relocation planning with weighted site scoring (hazard safety 35%, livelihood 20%, infrastructure 20%, school 15%, health 10%, distance penalty 2%/km), urgency-based allocation
- **Confidence Engine** — 5-component scoring (data quality, model coverage, input completeness, cascade strength, time certainty) with LOW/MEDIUM/HIGH levels
- **Decision Service** — Officer override layer with audit logging (ACCEPT/REJECT/MODIFY decisions across ACTION_RECOMMENDATION, RELOCATION_PLAN, EVACUATION_ORDER, RESOURCE_ALLOCATION categories)
- **Unified SHARMI Engine** — Single analysis endpoint composing all engines with decision override integration
- **API Hardening** — Middleware stack: Request ID tracking, structured JSON logging, in-memory rate limiting (120/min, 1000/hr), CORS support
- **Demo Integration** — Pre-configured scenarios (flood, landslide, cyclone, heatwave), unified dashboard endpoint, detailed health checks, recent audit log

> **Note:** Phases 3-10 demonstrate dependency propagation for the prototype. Dependency weights and the propagation threshold are synthetic demonstration parameters, not calibrated real-world infrastructure failure probabilities. Shadow Zone means an area affected indirectly through dependency propagation in the prototype — it does not represent a scientifically validated hazard boundary. Time-to-impact uses abstract time units — not minutes, hours, or days. Action recommendations are decision-support for officer review only — NOT autonomous emergency orders. Relocation optimization uses synthetic weighted scoring — NOT an automated evacuation order. Confidence scores are prototype indicators — NOT statistical confidence intervals.

Future phases will focus on SIH demo hardening, performance optimization, and production readiness. See [docs/development-phases.md](docs/development-phases.md) for the full roadmap.

## Technology Stack

| Layer      | Technology   |
|------------|-------------|
| Backend    | Python, FastAPI, Pydantic, NetworkX |
| Server     | Uvicorn |
| Testing    | pytest |

## Getting Started

### Prerequisites

- Python 3.10+

### Setup

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (Linux/Mac)
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run the development server
uvicorn app.main:app --reload

# Run tests
pytest -v
```

The backend will be available at `http://127.0.0.1:8000`.

- Interactive API docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Project Structure

```
sharmi/
├── backend/           # FastAPI backend application
│   ├── app/
│   │   ├── api/       # API endpoints (health, demo, risk, cascade, shadow-zone, impact, actions, relocation, confidence, decision, sharmi, demo_integration)
│   │   ├── middleware/ # Middleware stack (RequestID, Logging, RateLimit)
│   │   ├── models/    # Domain models (Phase 1)
│   │   ├── schemas/   # Pydantic schemas (Phase 2-10: risk, cascade, shadow_zone, time_to_impact, action, relocation, confidence, decision, sharmi)
│   │   └── services/  # Business logic (data_loader, risk_engine, cascade_engine, shadow_zone_engine, time_to_impact, action_engine, relocation_engine, confidence_engine, decision_service, sharmi_engine)
│   ├── tests/         # Test suite (334 tests)
│   └── requirements.txt
├── frontend/          # Future frontend dashboard
├── data/              # Demo datasets (Shivapur district)
├── docs/              # Architecture and development documentation
├── .gitignore
├── LICENSE
└── README.md
```

## Documentation

- [Architecture](docs/architecture.md) — Intended system architecture
- [Development Phases](docs/development-phases.md) — Phased development roadmap

## License

MIT License. See [LICENSE](LICENSE) for details.
