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

**Phase 1 — Demo Data & Domain Models (Complete)**

This repository is being built incrementally. Phase 0 established the project foundation. Phase 1 introduces:

- **Domain models** — Community, Hazard, InfrastructureNode, Dependency, RelocationSite with Pydantic validation
- **Synthetic Shivapur district dataset** — 10 communities, 15 infrastructure nodes, 4 hazards, 23 dependencies, 4 relocation sites
- **Data loading service** — Validates and serves demo data from JSON
- **Read-only API endpoints** — `/demo/communities`, `/demo/hazards`, `/demo/infrastructure`, `/demo/dependencies`, `/demo/relocation/sites`

Future phases will introduce the risk engine, cascade simulation, relocation optimizer, and more. See [docs/development-phases.md](docs/development-phases.md) for the full roadmap.

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
│   │   ├── api/       # API endpoints (health, demo)
│   │   ├── models/    # Domain models (Phase 1)
│   │   ├── schemas/   # Pydantic schemas (future)
│   │   └── services/  # Business logic (data_loader)
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
