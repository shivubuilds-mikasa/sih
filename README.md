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

**Phase 2 — Direct Risk Engine (Complete)**

This repository is being built incrementally. Phase 0 established the project foundation. Phase 1 introduced domain models and the Shivapur demo dataset. Phase 2 implements:

- **Direct Risk Engine** — Transparent weighted formula: `risk_score = 0.50×hazard_intensity + 0.30×exposure + 0.20×vulnerability`
- **Risk Classification** — LOW (0.00–0.29), MEDIUM (0.30–0.59), HIGH (0.60–1.00)
- **Explainable API** — Returns score, level, components, weights, and natural-language explanation
- **Ranked Risk Endpoint** — Communities ranked by direct risk from primary demo hazard (H001 flood)
- **Prototype Exposure Rule** — Deterministic: exposure = 1.0 if community in H001.affected_communities else 0.0

Future phases will introduce cascade simulation, shadow zones, relocation optimizer, and more. See [docs/development-phases.md](docs/development-phases.md) for the full roadmap.

> **Note:** This is a transparent prototype scoring model, not a scientifically calibrated disaster-risk forecast.

## Technology Stack

| Layer      | Technology   |
|------------|-------------|
| Backend    | Python, FastAPI, Pydantic |
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
│   │   ├── api/       # API endpoints (health, demo, risk)
│   │   ├── models/    # Domain models (Phase 1)
│   │   ├── schemas/   # Pydantic schemas (Phase 2: risk)
│   │   └── services/  # Business logic (data_loader, risk_engine)
│   ├── tests/         # Test suite
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
