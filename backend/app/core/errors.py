"""Helpers that keep provider/internal error text safe to store and show."""

from __future__ import annotations

import re

_MAX_LEN = 300
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"),  # OpenAI / Anthropic style keys
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[=:]\s*\S+"),
)
_URL_QUERY = re.compile(r"(https?://[^\s?#]+)\?[^\s]*")


def sanitize_error_text(value: object, max_len: int = _MAX_LEN) -> str:
    """One-line, length-capped error text with credentials and URL query strings removed.

    Provider exceptions can embed request URLs, headers or keys; the text is persisted on jobs and
    returned by the batch API, so it must not carry them.
    """
    text = " ".join(str(value).split())
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    text = _URL_QUERY.sub(r"\1", text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
