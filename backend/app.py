"""Create the local FastAPI application and attach the feature route groups."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from backend.api import chat, settings, stories
from backend.config import get_settings
from backend.observability import request_id_context

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    """Keep app construction explicit so local server startup stays predictable."""

    app = FastAPI(title="Mythos", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def correlate_requests(request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Give each response and its provider logs a shared diagnostic id."""

        request_id = uuid.uuid4().hex
        token = request_id_context.set(request_id)
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled API exception request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise
        finally:
            request_id_context.reset(token)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "API response request_id=%s method=%s path=%s status=%d duration_ms=%d",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            round((time.monotonic() - started) * 1000),
        )
        return response

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
