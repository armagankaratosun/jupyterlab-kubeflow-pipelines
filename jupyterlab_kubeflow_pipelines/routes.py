"""
Server routes for the JupyterLab extension.

Keep the public entrypoint stable for the JupyterLab extension template
(`setup_route_handlers`) while the implementation lives under
`jupyterlab_kubeflow_pipelines.server`.
"""

from __future__ import annotations

from .server.routes import setup_handlers


def setup_route_handlers(web_app) -> None:
    setup_handlers(web_app)
