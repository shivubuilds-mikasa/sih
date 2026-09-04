"""FastAPI application entry point for SHARMI backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.demo import router as demo_router
from .api.demo_integration import router as demo_integration_router
from .api.risk import router as risk_router
from .api.cascade import router as cascade_router
from .api.shadow_zone import router as shadow_zone_router
from .api.time_to_impact import router as time_to_impact_router
from .api.action import router as action_router
from .api.relocation import router as relocation_router
from .api.confidence import router as confidence_router
from .api.decision import router as decision_router
from .api.sharmi import router as sharmi_router
from .config import settings
from .middleware.request_id import RequestIDMiddleware
from .middleware.logging import LoggingMiddleware
from .middleware.rate_limit import RateLimitMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware (order matters: outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, requests_per_hour=1000)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(demo_router)
app.include_router(demo_integration_router)
app.include_router(risk_router)
app.include_router(cascade_router)
app.include_router(shadow_zone_router)
app.include_router(time_to_impact_router)
app.include_router(action_router)
app.include_router(relocation_router)
app.include_router(confidence_router)
app.include_router(decision_router)
app.include_router(sharmi_router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning service name."""
    return {"service": settings.APP_NAME}
