from fastapi import FastAPI

from app.api.datasets import router as datasets_router
from app.api.health import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(title="FarmLab Investigator", version="1.0.0")
    application.include_router(health_router)
    application.include_router(datasets_router)
    return application


app = create_app()
