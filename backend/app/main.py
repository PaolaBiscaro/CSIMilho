from pathlib import Path

from fastapi import FastAPI

from app.api.datasets import router as datasets_router
from app.api.diagnostics import router as diagnostics_router
from app.api.gemini import router as gemini_router
from app.api.health import router as health_router
from app.api.investigations import router as investigations_router
from app.frontend import FRONTEND_DIST, FrontendFiles, FrontendMount


def create_app(*, frontend_dist: Path | None = None) -> FastAPI:
    application = FastAPI(title="FarmLab Investigator", version="1.0.0")
    application.include_router(health_router)
    application.include_router(gemini_router)
    application.include_router(datasets_router)
    application.include_router(diagnostics_router)
    application.include_router(investigations_router)
    application.router.routes.append(FrontendMount(
        "/", app=FrontendFiles(frontend_dist if frontend_dist is not None else FRONTEND_DIST), name="frontend",
    ))
    return application


app = create_app()
