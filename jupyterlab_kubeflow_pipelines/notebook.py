from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .run import Run


class PipelineAlreadyExistsError(ValueError):
    pass


@dataclass(frozen=True)
class PipelineRef:
    pipeline_id: str
    pipeline_name: str

    def open_ui(self) -> None:
        """
        Ask the JupyterLab extension to open the pipeline details view.
        """
        try:
            from IPython.display import Javascript, display
        except ImportError:
            raise RuntimeError(
                "IPython is required to open pipeline UI from a notebook."
            )

        payload = json.dumps(
            {
                "type": "kfp-open-pipeline",
                "pipelineId": self.pipeline_id,
                "label": self.pipeline_name,
            }
        )
        display(Javascript(f"window.top.postMessage({payload}, '*');"))


@dataclass(frozen=True)
class PipelineVersionRef:
    pipeline_id: str
    pipeline_name: str | None
    version_id: str
    version_name: str

    def open_ui(self) -> None:
        """
        Ask the JupyterLab extension to open the parent pipeline details view.
        """
        try:
            from IPython.display import Javascript, display
        except ImportError:
            raise RuntimeError(
                "IPython is required to open pipeline UI from a notebook."
            )

        label = self.pipeline_name or f"Pipeline {self.pipeline_id}"
        payload = json.dumps(
            {
                "type": "kfp-open-pipeline",
                "pipelineId": self.pipeline_id,
                "label": label,
            }
        )
        display(Javascript(f"window.top.postMessage({payload}, '*');"))


@dataclass
class KFPClient:
    """
    Notebook-friendly KFP client for interactive use.

    This client wraps the KFP Python SDK, but also emits small bits of HTML/JS so
    the JupyterLab extension can open run details tabs (and request termination)
    without the user needing to copy/paste IDs.
    """

    endpoint: str = "http://localhost:8080"
    namespace: str = "kubeflow"
    _client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from kfp import Client

        self.endpoint = self.endpoint.rstrip("/")
        self._client = Client(host=self.endpoint, namespace=self.namespace)

    @property
    def sdk(self) -> Any:
        """
        Access to the underlying KFP Python SDK client for advanced operations.
        """
        return self._client

    def sync_to_jupyterlab(self) -> None:
        """
        Update the JupyterLab extension settings from this notebook client.

        The notebook kernel and the JupyterLab UI keep separate configuration state.
        This method asks the frontend extension to persist `endpoint` and `namespace`
        to the server-backed settings (token is intentionally not sent).
        """
        try:
            from IPython.display import Javascript, display
        except ImportError:
            raise RuntimeError(
                "IPython is required to sync config to the JupyterLab extension."
            )

        payload = json.dumps(
            {
                "type": "kfp-set-config",
                "endpoint": self.endpoint,
                "namespace": self.namespace,
            }
        )
        display(Javascript(f"window.top.postMessage({payload}, '*');"))

    def _ensure_experiment_id(self, experiment_name: str) -> str:
        try:
            exp = self._client.get_experiment(
                experiment_name=experiment_name, namespace=self.namespace
            )
            return exp.experiment_id
        except Exception:
            exp = self._client.create_experiment(
                name=experiment_name, namespace=self.namespace
            )
            return exp.experiment_id

    def _find_pipeline_by_name(self, pipeline_name: str) -> Any | None:
        page_token = ""
        page_size = 100
        for _ in range(50):
            resp = self._client.list_pipelines(
                page_token=page_token,
                page_size=page_size,
                namespace=self.namespace,
            )
            for p in getattr(resp, "pipelines", []) or []:
                if getattr(p, "display_name", None) == pipeline_name:
                    return p
            page_token = getattr(resp, "next_page_token", "") or ""
            if not page_token:
                return None
        return None

    def _latest_pipeline_version_id(self, *, pipeline_id: str) -> str:
        resp = self._client.list_pipeline_versions(
            pipeline_id=pipeline_id,
            page_size=100,
        )
        versions = getattr(resp, "pipeline_versions", []) or []
        if not versions:
            raise ValueError(
                f"Pipeline {pipeline_id} has no versions. "
                "Create a version first (register_pipeline_version_from_func) or run from a package."
            )

        def version_ts(v: Any) -> float:
            created_at = getattr(v, "created_at", None)
            if created_at is None:
                return 0.0
            if hasattr(created_at, "timestamp"):
                try:
                    return float(created_at.timestamp())
                except Exception:
                    return 0.0
            if isinstance(created_at, str):
                try:
                    parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    return float(parsed.timestamp())
                except Exception:
                    return 0.0
            return 0.0

        latest = max(versions, key=version_ts)
        version_id = getattr(latest, "pipeline_version_id", None)
        if not version_id:
            raise ValueError(
                f"Could not determine pipeline_version_id for pipeline {pipeline_id}."
            )
        return version_id

    def create_run_from_func(
        self,
        pipeline_func: Any,
        *,
        arguments: Mapping[str, Any] | None = None,
        experiment_name: str = "Default",
        run_name: str | None = None,
    ) -> Run:
        """
        Create a run from an in-memory pipeline function.

        Note: this may create runs that are not listed under the Pipelines page
        in the KFP UI (deployment-dependent). Use `register_pipeline_and_run_from_func()`
        if you want the run to be tied to a registered pipeline.
        """
        run = self._client.create_run_from_pipeline_func(
            pipeline_func=pipeline_func,
            arguments=dict(arguments or {}),
            experiment_name=experiment_name,
            run_name=run_name,
            namespace=self.namespace,
        )
        run_id = run.run_id
        label = run_name or getattr(pipeline_func, "__name__", "run")
        self._display_run_submitted(run_id=run_id, label=label)
        return Run(run_id=run_id, label=label, _kfp_client=self._client)

    def create_run_from_pipeline(
        self,
        *,
        pipeline_id: str,
        version_id: str | None = None,
        arguments: Mapping[str, Any] | None = None,
        experiment_name: str = "Default",
        run_name: str | None = None,
    ) -> Run:
        experiment_id = self._ensure_experiment_id(experiment_name)
        job_name = run_name or f"run-{pipeline_id}"
        resolved_version_id = version_id or self._latest_pipeline_version_id(
            pipeline_id=pipeline_id
        )
        run = self._client.run_pipeline(
            experiment_id=experiment_id,
            job_name=job_name,
            pipeline_id=pipeline_id,
            version_id=resolved_version_id,
            params=dict(arguments or {}),
        )
        self._display_run_submitted(run_id=run.run_id, label=job_name)
        return Run(run_id=run.run_id, label=job_name, _kfp_client=self._client)

    def create_run_from_pipeline_version(
        self,
        *,
        version_id: str,
        arguments: Mapping[str, Any] | None = None,
        experiment_name: str = "Default",
        run_name: str | None = None,
    ) -> Run:
        experiment_id = self._ensure_experiment_id(experiment_name)
        job_name = run_name or f"run-{version_id}"
        run = self._client.run_pipeline(
            experiment_id=experiment_id,
            job_name=job_name,
            version_id=version_id,
            params=dict(arguments or {}),
        )
        self._display_run_submitted(run_id=run.run_id, label=job_name)
        return Run(run_id=run.run_id, label=job_name, _kfp_client=self._client)

    def register_pipeline_from_func(
        self,
        pipeline_func: Any,
        *,
        pipeline_name: str,
        description: str | None = None,
    ) -> PipelineRef:
        """
        Register a new pipeline from a pipeline function.

        Errors if a pipeline with the same name exists.
        """
        existing = self._find_pipeline_by_name(pipeline_name)
        if existing is not None:
            raise PipelineAlreadyExistsError(
                f"Pipeline '{pipeline_name}' already exists. "
                "Use a unique pipeline_name, or create a new version via "
                "register_pipeline_version_from_func(...)."
            )

        pipeline = self._client.upload_pipeline_from_pipeline_func(
            pipeline_func=pipeline_func,
            pipeline_name=pipeline_name,
            description=description,
            namespace=self.namespace,
        )
        ref = PipelineRef(pipeline_id=pipeline.pipeline_id, pipeline_name=pipeline_name)
        self._display_pipeline_published(
            pipeline_id=ref.pipeline_id, label=ref.pipeline_name
        )
        return ref

    def register_pipeline_from_yaml(
        self,
        pipeline_yaml: str,
        *,
        pipeline_name: str,
        description: str | None = None,
    ) -> PipelineRef:
        """
        Register a new pipeline from a compiled KFP v2 pipeline YAML string.

        Errors if a pipeline with the same name exists.
        """
        existing = self._find_pipeline_by_name(pipeline_name)
        if existing is not None:
            raise PipelineAlreadyExistsError(
                f"Pipeline '{pipeline_name}' already exists. "
                "Use a unique pipeline_name, or create a new version via "
                "register_pipeline_version_from_func(...)."
            )

        pipeline_yaml = (pipeline_yaml or "").strip()
        if not pipeline_yaml:
            raise ValueError("pipeline_yaml is required.")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".yaml", delete=False, mode="w", encoding="utf-8"
            ) as tmp:
                tmp.write(pipeline_yaml)
                tmp_path = tmp.name

            pipeline = self._client.upload_pipeline(
                pipeline_package_path=tmp_path,
                pipeline_name=pipeline_name,
                description=description,
                namespace=self.namespace,
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        ref = PipelineRef(pipeline_id=pipeline.pipeline_id, pipeline_name=pipeline_name)
        self._display_pipeline_published(
            pipeline_id=ref.pipeline_id, label=ref.pipeline_name
        )
        return ref

    def register_pipeline_version_from_func(
        self,
        pipeline_func: Any,
        *,
        pipeline_version_name: str,
        pipeline_id: str | None = None,
        pipeline_name: str | None = None,
        description: str | None = None,
    ) -> PipelineVersionRef:
        """
        Register a new pipeline version for an existing pipeline.
        """
        if pipeline_id is None and pipeline_name is None:
            raise ValueError("Provide pipeline_id or pipeline_name.")

        if pipeline_id is None and pipeline_name is not None:
            existing = self._find_pipeline_by_name(pipeline_name)
            if existing is None:
                raise ValueError(f"Pipeline '{pipeline_name}' was not found.")
            pipeline_id = existing.pipeline_id

        version = self._client.upload_pipeline_version_from_pipeline_func(
            pipeline_func=pipeline_func,
            pipeline_version_name=pipeline_version_name,
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            description=description,
        )
        ref = PipelineVersionRef(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            version_id=version.pipeline_version_id,
            version_name=pipeline_version_name,
        )
        self._display_pipeline_published(
            pipeline_id=ref.pipeline_id,
            label=ref.pipeline_name or ref.version_name,
        )
        return ref

    def register_pipeline_and_run_from_func(
        self,
        pipeline_func: Any,
        *,
        pipeline_name: str,
        pipeline_description: str | None = None,
        arguments: Mapping[str, Any] | None = None,
        experiment_name: str = "Default",
        run_name: str | None = None,
    ) -> Run:
        """
        Composite convenience: register a new pipeline, then create a run for it.

        If the pipeline name already exists, this raises `PipelineAlreadyExistsError`
        and tells the user to either pick a unique name or publish a new version.
        """
        pipeline = self.register_pipeline_from_func(
            pipeline_func,
            pipeline_name=pipeline_name,
            description=pipeline_description,
        )
        return self.create_run_from_pipeline(
            pipeline_id=pipeline.pipeline_id,
            arguments=arguments,
            experiment_name=experiment_name,
            run_name=run_name or pipeline_name,
        )

    def _display_card(
        self,
        *,
        title: str,
        id_label: str,
        id_value: str,
        button_text: str,
        open_payload: str,
        open_url: str,
    ) -> None:
        try:
            from IPython.display import HTML, display
        except ImportError:
            return

        html = f"""
        <div style="padding: 10px; border: 1px solid #2196F3; border-radius: 4px; background: #E3F2FD; margin: 10px 0;">
          <p style="margin: 0 0 10px 0; font-weight: bold; color: #1976D2;">{title}</p>
          <p style="margin: 0; font-size: 13px;">{id_label}: <code>{id_value}</code></p>
          <div style="margin-top: 10px;">
            <button
              onclick='window.top.postMessage({open_payload}, \"*\")'
              style="background: #2196F3; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold;"
            >
              {button_text}
            </button>
            <a href="{open_url}" target="_blank" style="margin-left: 10px; font-size: 12px; color: #1976D2;">Open in KFP UI (New Window)</a>
          </div>
        </div>
        """
        display(HTML(html))

    def _display_run_submitted(self, *, run_id: str, label: str) -> None:
        payload = json.dumps({"type": "kfp-open-run", "runId": run_id, "label": label})
        open_in_kfp = f"{self.endpoint}/#/runs/details/{run_id}"
        self._display_card(
            title="Pipeline Run Submitted",
            id_label="Run ID",
            id_value=run_id,
            button_text="Open Details in JupyterLab Tab",
            open_payload=payload,
            open_url=open_in_kfp,
        )

    def _display_pipeline_published(self, *, pipeline_id: str, label: str) -> None:
        payload = json.dumps(
            {"type": "kfp-open-pipeline", "pipelineId": pipeline_id, "label": label}
        )
        open_in_kfp = f"{self.endpoint}/#/pipelines/details/{pipeline_id}"
        self._display_card(
            title="Pipeline Published",
            id_label="Pipeline ID",
            id_value=pipeline_id,
            button_text="Open Pipeline in JupyterLab Tab",
            open_payload=payload,
            open_url=open_in_kfp,
        )
