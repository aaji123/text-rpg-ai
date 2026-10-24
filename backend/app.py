"""Create the local FastAPI application and attach the feature route groups."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat, settings, stories
from backend.config import get_settings


def create_app() -> FastAPI:
    """Keep app construction explicit so local server startup stays predictable."""

    app = FastAPI(title="Text RPG AI", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(stories.router)
    app.include_router(chat.router)
    app.include_router(settings.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Offer a path-free readiness check for the frontend connection badge."""

        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_settings()
    uvicorn.run("backend.app:app", host=config.app_host, port=config.app_port, reload=True)
