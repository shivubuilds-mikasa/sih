# SHARMI Backend

FastAPI backend for the SHARMI disaster-management decision-support system.

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest -v
```

## Endpoints

| Method | Path      | Description       |
|--------|-----------|-------------------|
| GET    | `/`       | Service name      |
| GET    | `/health` | Health check      |
| GET    | `/docs`   | Swagger UI        |
| GET    | `/redoc`  | ReDoc             |
