"""Serve only the Vite output, after all API routes, with an SPA fallback."""
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse
from starlette.routing import Match, Mount
from starlette.staticfiles import StaticFiles
from starlette._utils import get_route_path


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class FrontendMount(Mount):
    def matches(self, scope):
        # Let FastAPI retain its 404/405 responses for APIs and documentation.
        if scope["type"] != "http" or get_route_path(scope).strip("/").split("/")[0] in {
            "api", "docs", "redoc", "openapi.json",
        }:
            return Match.NONE, {}
        return super().matches(scope)


class FrontendFiles(StaticFiles):
    def __init__(self, directory: Path):
        super().__init__(directory=directory, check_dir=False)

    async def check_config(self) -> None:
        # A fresh API checkout must start before `pnpm build`. Missing output
        # is handled below, and a later build becomes available without restart.
        pass

    async def get_response(self, path, scope):
        segments = scope["path"].strip("/").split("/")
        if any(part.startswith(".") or "\\" in part or ":" in part for part in segments):
            raise HTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            # Never substitute HTML for a missing asset or a non-GET request.
            if error.status_code != 404 or segments[0] == "assets" or Path(path).suffix:
                raise
            try:
                response = await super().get_response("index.html", scope)
            except HTTPException as missing:
                if missing.status_code != 404:
                    raise
                return PlainTextResponse(
                    "Interface ainda não compilada. Execute pnpm build no diretório frontend e recarregue esta página.",
                    status_code=503, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
                )
            response.headers["Cache-Control"] = "no-cache"
        if path == "index.html":
            response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
