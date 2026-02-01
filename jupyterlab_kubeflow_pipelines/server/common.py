from __future__ import annotations

from ..config import normalize_endpoint


def base_kfp_endpoint(endpoint: str | None) -> str:
    normalized = normalize_endpoint(endpoint)
    if not normalized:
        raise ValueError("KFP endpoint is not configured in the backend.")
    return normalized
