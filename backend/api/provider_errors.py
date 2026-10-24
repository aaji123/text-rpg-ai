"""Translate classified Groq failures into safe API errors and diagnostics."""

import logging
import math

from fastapi import HTTPException

from backend.ai.groq_client import GroqRequestError
from backend.observability import request_id_context

logger = logging.getLogger(__name__)


def to_http_exception(error: GroqRequestError) -> HTTPException:
    """Log the upstream failure signature and return a credential-safe response."""

    logger.error(
        "Groq API failure request_id=%s operation=%s category=%s provider_status=%s provider_request_id=%s attempts=%d",
        request_id_context.get(),
        error.operation,
        error.category,
        error.provider_status if error.provider_status is not None else "unknown",
        error.provider_request_id or "unknown",
        error.attempts,
    )
    headers = None
    retry_after = error.retry_after
    if error.category == "rate_limit" and retry_after is None:
        retry_after = 2
    if retry_after is not None and math.isfinite(retry_after):
        headers = {"Retry-After": str(max(1, min(60, math.ceil(retry_after))))}
    request_id = request_id_context.get()
    detail = f"{error.public_detail} Request ID: {request_id}."
    return HTTPException(status_code=error.http_status, detail=detail, headers=headers)
