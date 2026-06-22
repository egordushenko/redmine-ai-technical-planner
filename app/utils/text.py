from __future__ import annotations

import hashlib
import re


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_secret_values(value: str) -> str:
    return re.sub(r"(?i)(api[_-]?key|token|password|secret)=([^\\s]+)", r"\1=<redacted>", value)
