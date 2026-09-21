from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_SECRET_KEY_RE = re.compile(
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|authorization|cookie|set-cookie|session|totp|otp|recovery[_-]?code|private[_-]?key)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{32,}\b")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PUBLIC_FINGERPRINT_KEY_RE = re.compile(
    r"(?:^|_)(?:hash|digest|sha256|checksum|revision|action_id)$", re.IGNORECASE
)
_PUBLIC_CODE_KEY_RE = re.compile(r"(?:^|_)(?:code|failure_code|error_code|status|state)$", re.IGNORECASE)
_PUBLIC_CODE_VALUE_RE = re.compile(r"[A-Z][A-Z0-9_]{2,128}")
_PUBLIC_FINGERPRINT_VALUE_RE = re.compile(
    r"(?:[a-f0-9]{32,128}|[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12})",
    re.IGNORECASE,
)


class Redactor:
    """Best-effort structural redaction.

    Redaction is defense in depth. Callers must avoid collecting secrets at source.
    """

    def __init__(self, *, redact_email: bool = False) -> None:
        self.redact_email = redact_email

    def redact(self, value: Any, *, key_hint: str | None = None) -> Any:
        if key_hint and _SECRET_KEY_RE.search(key_hint):
            return "[REDACTED]"
        if isinstance(value, Mapping):
            return {str(k): self.redact(v, key_hint=str(k)) for k, v in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [self.redact(v) for v in value]
        if isinstance(value, bytes):
            return f"[BINARY:{len(value)}]"
        if isinstance(value, str):
            if key_hint:
                if (
                    _PUBLIC_FINGERPRINT_KEY_RE.search(key_hint)
                    and _PUBLIC_FINGERPRINT_VALUE_RE.fullmatch(value)
                ):
                    return value
                if _PUBLIC_CODE_KEY_RE.search(key_hint) and _PUBLIC_CODE_VALUE_RE.fullmatch(value):
                    return value
            text = _BEARER_RE.sub("[REDACTED_AUTH]", value)
            text = _LONG_TOKEN_RE.sub("[REDACTED_TOKEN]", text)
            if self.redact_email:
                text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
            return text
        return value

    def contains_secret_shape(self, value: Any, *, key_hint: str | None = None) -> bool:
        if key_hint and _SECRET_KEY_RE.search(key_hint):
            return True
        if isinstance(value, Mapping):
            return any(self.contains_secret_shape(v, key_hint=str(k)) for k, v in value.items())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return any(self.contains_secret_shape(v) for v in value)
        if isinstance(value, str):
            if key_hint:
                if (
                    _PUBLIC_FINGERPRINT_KEY_RE.search(key_hint)
                    and _PUBLIC_FINGERPRINT_VALUE_RE.fullmatch(value)
                ):
                    return False
                if _PUBLIC_CODE_KEY_RE.search(key_hint) and _PUBLIC_CODE_VALUE_RE.fullmatch(value):
                    return False
            return bool(_BEARER_RE.search(value) or _LONG_TOKEN_RE.search(value))
        return False
