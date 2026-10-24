"""Wrap Groq requests with bounded retries, deadlines, and safe diagnostics."""

import asyncio
import logging
import re
import time

from groq import APIConnectionError, APIStatusError, APITimeoutError, AsyncGroq

from backend.observability import request_id_context

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}


class GroqRequestError(Exception):
    """Expose a classified, credential-free failure to the API layer."""

    def __init__(
        self,
        operation: str,
        category: str,
        attempts: int,
        provider_status: int | None = None,
        provider_request_id: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Keep only diagnostic fields needed for safe logging and HTTP mapping."""

        super().__init__(f"Groq {operation} failed: {category}")
        self.operation = operation
        self.category = category
        self.attempts = attempts
        self.provider_status = provider_status
        self.provider_request_id = provider_request_id
        self.retry_after = retry_after

    @property
    def http_status(self) -> int:
        """Map upstream failures to an actionable local HTTP response."""

        if self.category == "timeout":
            return 504
        if self.category == "rate_limit":
            return 503
        return 502

    @property
    def public_detail(self) -> str:
        """Describe the failure without returning provider response contents."""

        if self.category == "timeout":
            return "Groq did not respond before the request timed out. Please retry."
        if self.category == "rate_limit":
            return "Groq is rate limiting requests. Please retry shortly."
        if self.category == "connection":
            return "The backend could not connect to Groq. Check the network and retry."
        if self.category == "empty_response":
            return "Groq returned an empty response. Please retry."
        if self.provider_status in {401, 403}:
            return "Groq rejected the configured API credentials. Check the key in .env."
        if self.provider_status:
            return f"Groq returned an upstream error (HTTP {self.provider_status}). Please retry."
        return "The Groq service could not complete the request. Please retry."


class GroqNarrator:
    """Send grounded game messages while recording request-level diagnostics."""

    def __init__(self, api_key: str, model: str) -> None:
        """Use explicit network limits and disable hidden SDK retries."""

        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        self.client = AsyncGroq(api_key=api_key, timeout=75.0, max_retries=0)
        self.model = model

    async def reply(self, system_prompt: str, message: str) -> str:
        """Stream one narrator or utility response through the common retry path."""

        return await self._complete("chat", system_prompt, message)

    async def brainstorm(self, system_prompt: str, idea: str) -> str:
        """Ask for structured campaign ideas through the common retry path."""

        return await self._complete("brainstorm", system_prompt, idea)

    async def generate_example(self, system_prompt: str) -> str:
        """Generate a short setup example through the common retry path."""

        return await self._complete(
            "example",
            system_prompt,
            "Generate one short example for the field described above.",
        )

    async def _complete(self, operation: str, system_prompt: str, user_message: str) -> str:
        """Retry only transient provider failures and report safe timing details."""

        started = time.monotonic()
        for attempt in range(1, MAX_ATTEMPTS + 1):
            parts: list[str] = []
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.6,
                    max_completion_tokens=2048,
                    top_p=0.95,
                    reasoning_effort="default",
                    stream=True,
                    stop=None,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    content = chunk.choices[0].delta.content
                    if content:
                        parts.append(content)
                result = "".join(parts).strip()
                if not result:
                    raise _EmptyGroqResponse()
                logger.info(
                    "Groq request succeeded operation=%s request_id=%s attempt=%d duration_ms=%d",
                    operation,
                    request_id_context.get(),
                    attempt,
                    round((time.monotonic() - started) * 1000),
                )
                return result
            except Exception as error:
                category, provider_status, provider_request_id, retry_after, retryable = _classify_error(error)
                if category == "empty_response":
                    retryable = True
                if retryable and attempt < MAX_ATTEMPTS:
                    delay = min(max(retry_after if retry_after is not None else 0.5 * (2 ** (attempt - 1)), 0.25), 8.0)
                    logger.warning(
                        "Groq request retry operation=%s request_id=%s provider_request_id=%s category=%s provider_status=%s attempt=%d max_attempts=%d retry_in_seconds=%.2f",
                        operation,
                        request_id_context.get(),
                        provider_request_id or "unknown",
                        category,
                        provider_status if provider_status is not None else "unknown",
                        attempt,
                        MAX_ATTEMPTS,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    "Groq request failed operation=%s request_id=%s provider_request_id=%s category=%s provider_status=%s attempts=%d duration_ms=%d exception_type=%s",
                    operation,
                    request_id_context.get(),
                    provider_request_id or "unknown",
                    category,
                    provider_status if provider_status is not None else "unknown",
                    attempt,
                    round((time.monotonic() - started) * 1000),
                    type(error).__name__,
                )
                raise GroqRequestError(
                    operation=operation,
                    category=category,
                    attempts=attempt,
                    provider_status=provider_status,
                    provider_request_id=provider_request_id,
                    retry_after=retry_after,
                ) from None
        raise GroqRequestError(operation, "unknown", MAX_ATTEMPTS)


class _EmptyGroqResponse(Exception):
    """Mark a completed but content-free stream so it can be retried once bounded."""


def _classify_error(error: Exception) -> tuple[str, int | None, str | None, float | None, bool]:
    """Extract status and request identifiers without recording provider bodies."""

    if isinstance(error, _EmptyGroqResponse):
        return "empty_response", None, None, None, True
    if isinstance(error, APITimeoutError):
        return "timeout", None, None, None, True
    if isinstance(error, APIConnectionError):
        return "connection", None, None, None, True
    if isinstance(error, APIStatusError):
        status = error.status_code
        response_id = error.response.headers.get("x-request-id") if error.response else None
        retry_header = None
        if error.response:
            retry_header = error.response.headers.get("retry-after") or error.response.headers.get("x-ratelimit-reset-requests")
        retry_after = _parse_retry_after(retry_header)
        category = "rate_limit" if status == 429 else "timeout" if status in {408, 504} else "provider_status"
        return category, status, response_id, retry_after, status in RETRYABLE_STATUSES
    return "unexpected_provider_error", None, None, None, False


def _parse_retry_after(value: str | None) -> float | None:
    """Accept numeric and seconds-suffixed provider backoff hints safely."""

    if not value:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\s*", value, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
