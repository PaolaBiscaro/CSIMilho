from fastapi import FastAPI

from app.api.datasets import router as datasets_router
from app.api.diagnostics import router as diagnostics_router
from app.api.gemini import router as gemini_router
from app.api.health import router as health_router
from app.api.investigations import router as investigations_router


def create_app() -> FastAPI:
    application = FastAPI(title="FarmLab Investigator", version="1.0.0")
    application.include_router(health_router)
    application.include_router(gemini_router)
    application.include_router(datasets_router)
    application.include_router(diagnostics_router)
    application.include_router(investigations_router)
    return application


app = create_app()
