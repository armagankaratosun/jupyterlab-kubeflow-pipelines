"""
Minimal local JupyterHub config for reproducing path-based KFP UI issues.

Usage:
  jupyterhub -f dev/jupyterhub-local/jupyterhub_config.py
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

c = get_config()  # noqa: F821

here = Path(__file__).resolve().parent
state_dir = here / ".jupyterhub"
state_dir.mkdir(parents=True, exist_ok=True)

# Path-based user URLs by default: /user/<name>/...
c.JupyterHub.bind_url = os.environ.get("JUPYTERHUB_BIND_URL", "http://127.0.0.1:8100")
c.JupyterHub.hub_bind_url = os.environ.get(
    "JUPYTERHUB_HUB_BIND_URL", "http://127.0.0.1:8101"
)
c.ConfigurableHTTPProxy.api_url = os.environ.get(
    "JUPYTERHUB_PROXY_API_URL", "http://127.0.0.1:8102"
)

# Optional: test subdomain routing if you provide a wildcard DNS host locally.
subdomain_host = os.environ.get("JUPYTERHUB_SUBDOMAIN_HOST", "").strip()
if subdomain_host:
    c.JupyterHub.subdomain_host = subdomain_host

c.JupyterHub.authenticator_class = "dummy"
c.Authenticator.allow_all = True
c.DummyAuthenticator.password = os.environ.get("JUPYTERHUB_PASSWORD", "devpass")

# Use JupyterHub's default single-user command (`jupyterhub-singleuser`).
# This avoids local environment differences around `jupyter-labhub`.
c.Spawner.default_url = "/lab"
c.Spawner.debug = True
c.Spawner.http_timeout = 60

c.JupyterHub.db_url = f"sqlite:///{state_dir / 'jupyterhub.sqlite'}"
c.JupyterHub.cookie_secret_file = str(state_dir / "jupyterhub_cookie_secret")
c.ConfigurableHTTPProxy.pid_file = str(state_dir / "jupyterhub-proxy.pid")

# Keep logs noisy for debugging proxy/auth flow.
c.JupyterHub.log_level = "DEBUG"
c.Application.log_level = "DEBUG"

# Prefer an explicit CHP command from env (used by local harness).
chp_cmd = os.environ.get("JUPYTERHUB_CHP_COMMAND", "").strip()
if chp_cmd:
    c.ConfigurableHTTPProxy.command = shlex.split(chp_cmd)
else:
    # Fallback for environments where configurable-http-proxy is not preinstalled.
    c.ConfigurableHTTPProxy.command = ["npx", "--yes", "configurable-http-proxy"]
