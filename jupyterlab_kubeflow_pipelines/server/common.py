from __future__ import annotations

from ..config import normalize_endpoint
from urllib.parse import parse_qsl, urlencode, urlparse


def base_kfp_endpoint(endpoint: str | None) -> str:
    normalized = normalize_endpoint(endpoint)
    if not normalized:
        raise ValueError("KFP endpoint is not configured in the backend.")
    return normalized


def base_kfp_ui_endpoint(endpoint: str | None) -> str:
    """
    Resolve the base endpoint used to proxy the KFP UI.

    In many Kubeflow Platform deployments, the API endpoint is the
    `ml-pipeline` service (often on :8888) while the UI shell is served by
    `ml-pipeline-ui` (typically on :80). When users configure the API endpoint,
    infer the UI endpoint for iframe proxying.
    """
    normalized = base_kfp_endpoint(endpoint)
    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").strip()
    if not hostname:
        return normalized

    # Convert well-known in-cluster API service name to UI service name.
    if hostname == "ml-pipeline" or hostname.startswith("ml-pipeline."):
        ui_hostname = "ml-pipeline-ui" + hostname[len("ml-pipeline") :]

        # Keep explicit custom ports, but drop common API/UI defaults.
        parsed_port = parsed.port
        if parsed_port in {None, 80, 8888}:
            netloc = ui_hostname
        else:
            netloc = f"{ui_hostname}:{parsed_port}"

        path = (parsed.path or "").rstrip("/")
        if path == "/":
            path = ""
        return f"{parsed.scheme}://{netloc}{path}"

    return normalized


def ensure_namespace_query(
    *, path: str, query: str, namespace: str | None
) -> str:
    """
    Ensure KFP v2beta1 list endpoints include a non-empty namespace.

    In multi-user deployments, list endpoints reject empty/missing namespace.
    """
    ns = (namespace or "").strip()
    if not ns:
        return query

    normalized_path = path.lstrip("/").rstrip("/")
    list_paths = {
        "apis/v1beta1/experiments",
        "apis/v1beta1/runs",
        "apis/v1beta1/jobs",
        "apis/v1beta1/pipelines",
        "apis/v1beta1/pipeline_versions",
        "apis/v2beta1/experiments",
        "apis/v2beta1/runs",
        "apis/v2beta1/jobs",
        "apis/v2beta1/pipelines",
        "apis/v2beta1/pipeline_versions",
    }
    if normalized_path not in list_paths:
        return query

    params = parse_qsl(query, keep_blank_values=True)
    found_namespace = False
    rewritten: list[tuple[str, str]] = []
    for key, value in params:
        if key == "namespace":
            found_namespace = True
            rewritten.append((key, value if value.strip() else ns))
        else:
            rewritten.append((key, value))

    if not found_namespace:
        rewritten.append(("namespace", ns))

    return urlencode(rewritten)
