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

**Phase 0 — Project Foundation**

This repository is being built incrementally. We are currently laying the groundwork: project structure, backend scaffolding, configuration, and testing infrastructure.

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
├── backend/          # FastAPI backend application
├── frontend/         # Future frontend dashboard
├── data/             # Future data assets and datasets
├── docs/             # Architecture and development documentation
├── .gitignore
├── LICENSE
└── README.md
```

## Documentation

- [Architecture](docs/architecture.md) — Intended system architecture
- [Development Phases](docs/development-phases.md) — Phased development roadmap

## License

MIT License. See [LICENSE](LICENSE) for details.
