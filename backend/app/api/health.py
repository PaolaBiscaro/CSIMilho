from fastapi import APIRouter

from app.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str | bool]:
    settings: Settings = get_settings()
    return {
        "status": "ok",
        "gemini_configured": settings.gemini_configured,
        "model": settings.gemini_model,
        "version": settings.app_version,
    }
