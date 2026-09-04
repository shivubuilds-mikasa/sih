"""FastAPI application entry point for SHARMI backend."""

from fastapi import FastAPI

from .api.health import router as health_router
from .api.demo import router as demo_router
from .config import settings

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router)
app.include_router(demo_router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint returning service name."""
    return {"service": settings.APP_NAME}
