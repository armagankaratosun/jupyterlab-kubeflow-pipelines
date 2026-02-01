from __future__ import annotations

import json
import os
import tempfile

from jupyter_server.base.handlers import APIHandler
from tornado import web

from .config import get_config
from .kfp_compiler import _normalize_kfp_host


def _find_pipeline_id_by_name(
    client, *, pipeline_name: str, namespace: str | None
) -> str | None:
    # Best-effort: try server-side filter first; fallback to client-side scan.
    filter_expr = f'display_name="{pipeline_name}"'
    try:
        resp = client.list_pipelines(
            page_size=50, filter=filter_expr, namespace=namespace
        )
        pipelines = getattr(resp, "pipelines", None) or []
        for p in pipelines:
            if getattr(p, "display_name", None) == pipeline_name:
                return getattr(p, "pipeline_id", None)
    except Exception:
        pass

    try:
        resp = client.list_pipelines(page_size=200, namespace=namespace)
        pipelines = getattr(resp, "pipelines", None) or []
        for p in pipelines:
            if getattr(p, "display_name", None) == pipeline_name:
                return getattr(p, "pipeline_id", None)
    except Exception:
        return None

    return None


class KfpImportPipelineHandler(APIHandler):
    """
    Import/register a pipeline from a YAML package (KFP v2 pipeline spec).

    This creates a *pipeline* (not a run). If the pipeline name already exists,
    we return 409 and include the existing pipeline_id so the client can offer
    "create a new version" as a follow-up action.
    """

    @web.authenticated
    async def post(self):
        try:
            body = json.loads(self.request.body or b"{}")
        except Exception:
            self.set_status(400)
            self.write(json.dumps({"error": "Invalid JSON body"}))
            return

        pipeline_yaml = (body.get("pipeline_yaml") or "").strip()
        pipeline_name = (body.get("pipeline_name") or "").strip()
        description = (body.get("description") or "").strip() or None

        if not pipeline_yaml:
            self.set_status(400)
            self.write(json.dumps({"error": "pipeline_yaml is required"}))
            return
        if not pipeline_name:
            self.set_status(400)
            self.write(json.dumps({"error": "pipeline_name is required"}))
            return

        cfg = get_config(self)
        if not cfg.endpoint:
            self.set_status(400)
            self.write(json.dumps({"error": "KFP endpoint is not configured"}))
            return

        try:
            host = _normalize_kfp_host(cfg.endpoint)
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"error": str(e)}))
            return

        import kfp

        client_args: dict[str, object] = {"host": host}
        if cfg.token:
            client_args["existing_token"] = cfg.token

        try:
            client = kfp.Client(**client_args)
        except Exception as e:
            self.set_status(502)
            self.write(
                json.dumps(
                    {
                        "error": "Failed to connect to Kubeflow Pipelines.",
                        "detail": str(e),
                        "endpoint": cfg.endpoint,
                        "normalized_host": host,
                    }
                )
            )
            return

        namespace = cfg.namespace or None
        existing_id = _find_pipeline_id_by_name(
            client, pipeline_name=pipeline_name, namespace=namespace
        )
        if existing_id:
            self.set_status(409)
            self.write(
                json.dumps(
                    {
                        "error": "A pipeline with this name already exists.",
                        "pipeline_id": existing_id,
                        "pipeline_name": pipeline_name,
                    }
                )
            )
            return

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".yaml", delete=False, mode="w", encoding="utf-8"
            ) as tmp:
                tmp.write(pipeline_yaml)
                tmp_path = tmp.name

            pipeline = client.upload_pipeline(
                pipeline_package_path=tmp_path,
                pipeline_name=pipeline_name,
                description=description,
                namespace=namespace,
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        pipeline_id = getattr(pipeline, "pipeline_id", None)
        self.write(
            json.dumps(
                {
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline_name,
                    "url": f"{host}/#/pipelines/details/{pipeline_id}",
                }
            )
        )
