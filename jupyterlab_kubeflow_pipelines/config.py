from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass
class KfpConfig:
    endpoint: str | None = None
    namespace: str = "kubeflow"
    token: str | None = None


_CONFIG_BY_USER: dict[str, KfpConfig] = {}


class _UnsetType:
    pass


_UNSET = _UnsetType()


def _user_key(handler: Any) -> str:
    user = getattr(handler, "current_user", None)
    if isinstance(user, dict):
        return user.get("name") or user.get("username") or "default"
    if isinstance(user, str):
        return user
    return "default"


def normalize_endpoint(endpoint: str | None) -> str | None:
    """
    Normalize a user-provided endpoint to a base URL (scheme://host:port[/path]).

    - Preserves an optional path prefix (e.g. /pipeline).
    - Strips query/fragment.
    - Adds http:// if no scheme is provided.
    - Rejects localhost endpoints without an explicit port.
    """
    if endpoint is None:
        return None

    endpoint = endpoint.strip()
    if not endpoint:
        return None

    if any(ch.isspace() for ch in endpoint):
        raise ValueError("Endpoint must not contain whitespace.")

    if "://" not in endpoint:
        endpoint = f"http://{endpoint}"

    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Endpoint must look like 'http(s)://host:port'.")

    hostname = parsed.hostname or ""
    if parsed.port is None and hostname in {"localhost", "127.0.0.1"}:
        raise ValueError(
            "For localhost, include an explicit port (e.g. http://localhost:8080)."
        )

    path = (parsed.path or "").rstrip("/")
    if path == "/":
        path = ""

    return f"{parsed.scheme}://{parsed.netloc}{path}"


def get_config(handler: Any) -> KfpConfig:
    key = _user_key(handler)
    cfg = _CONFIG_BY_USER.get(key)
    if cfg is None:
        cfg = KfpConfig()
        _CONFIG_BY_USER[key] = cfg
    return cfg


def get_public_config(handler: Any) -> dict[str, Any]:
    cfg = get_config(handler)
    return {
        "endpoint": cfg.endpoint,
        "namespace": cfg.namespace,
        "has_token": bool(cfg.token),
    }


def update_config(
    handler: Any,
    *,
    endpoint: str | None,
    namespace: str | None,
    token: str | None | object,
) -> KfpConfig:
    """
    Update stored config for the current user.

    - If token is _UNSET, keep existing token.
    - If token is ''/None, clear token.
    """
    cfg = get_config(handler)

    if endpoint is not None:
        cfg.endpoint = normalize_endpoint(endpoint)
    if namespace is not None:
        ns = (namespace or "").strip()
        if ns and any(ch.isspace() for ch in ns):
            raise ValueError("Namespace must not contain whitespace.")
        cfg.namespace = ns or "kubeflow"

    if token is not _UNSET:
        cfg.token = (token or None) if isinstance(token, str) else None

    return cfg
