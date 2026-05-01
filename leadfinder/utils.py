from __future__ import annotations

import hashlib
from urllib.parse import urlparse


def ensure_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return ""
    return candidate


def build_dedupe_key(*parts: str) -> str:
    normalized = "|".join(_normalize(part) for part in parts if str(part).strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def parse_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _normalize(value: str) -> str:
    return "".join(ch.lower() for ch in str(value).strip() if ch.isalnum())
