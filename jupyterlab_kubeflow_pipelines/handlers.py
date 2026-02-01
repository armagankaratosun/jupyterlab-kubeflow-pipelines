"""
Compatibility wrapper for server-side routes.

Historically, all Jupyter Server handlers lived in this file.
They have been moved under `jupyterlab_kubeflow_pipelines.server` to keep a clear
separation between server (backend) and notebook helpers.
"""

from __future__ import annotations

from .server.routes import setup_handlers

__all__ = ["setup_handlers"]
