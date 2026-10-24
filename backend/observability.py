"""Share a per-request correlation id with routes and provider diagnostics."""

from contextvars import ContextVar


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
