from __future__ import annotations

import re
from typing import Any


_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsk-[A-Za-z0-9]{10,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9\-\._~\+\/]+=*\b", re.IGNORECASE),
]


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        out = value
        for pat in _PATTERNS:
            out = pat.sub("[REDACTED]", out)
        return out
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    return value

