from __future__ import annotations

import json
import time

from .proxy_root import KfpRootProxyHandler
from .proxy_ui import BRIDGE_COOKIE_NAME


class BaseUrlRedirectHandler(KfpRootProxyHandler):
    """
    Authorize and proxy root-relative KFP UI calls on JupyterHub.

    Some embedded UIs (notably KFP UI) issue root-relative requests like
    `/ml_metadata.MetadataStoreService/...` even when Jupyter Server is mounted
    under a base_url (e.g. `/user/<name>/` on JupyterHub).

    Those calls may miss JupyterHub's path-scoped auth cookies. We therefore
    accept a short-lived signed bridge cookie minted by `KfpUIProxyHandler` and
    proxy the request directly using the existing KFP proxy stack.
    """

    def initialize(self, *, base_url: str) -> None:  # type: ignore[override]
        self._base_url = base_url

    def check_xsrf_cookie(self) -> None:
        # Auth is enforced via the signed bridge cookie; this endpoint is proxy-only.
        return

    def _bridge_cookie_ok(self) -> bool:
        raw = self.get_secure_cookie(BRIDGE_COOKIE_NAME, max_age_days=1)
        if not raw:
            self.log.warning("KFP root bridge: missing signed bridge cookie")
            return False

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.log.warning("KFP root bridge: invalid bridge cookie payload")
            return False

        if payload.get("base_url") != self._base_url:
            self.log.warning("KFP root bridge: base_url mismatch in bridge cookie")
            return False

        expires_at = payload.get("exp")
        if not isinstance(expires_at, int) or expires_at < int(time.time()):
            self.log.warning("KFP root bridge: expired bridge cookie")
            return False

        expected_session_id = payload.get("sid", "")
        current_session_id = self.get_cookie("jupyterhub-session-id", default="") or ""
        if (
            isinstance(expected_session_id, str)
            and expected_session_id
            and current_session_id
            and expected_session_id != current_session_id
        ):
            self.log.warning("KFP root bridge: session id mismatch for bridge cookie")
            return False

        return True

    async def _proxy_if_authorized(self) -> None:
        if not self._bridge_cookie_ok():
            self.set_status(403)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps({"error": "Forbidden"}))
            return
        self.log.info("KFP root bridge: authorized %s %s", self.request.method, self.request.path)
        await self._handle_root()

    async def get(self, *args) -> None:
        await self._proxy_if_authorized()

    async def post(self, *args) -> None:
        await self._proxy_if_authorized()

    async def put(self, *args) -> None:
        await self._proxy_if_authorized()

    async def patch(self, *args) -> None:
        await self._proxy_if_authorized()

    async def delete(self, *args) -> None:
        await self._proxy_if_authorized()

    async def head(self, *args) -> None:
        await self._proxy_if_authorized()

    async def options(self, *args) -> None:
        await self._proxy_if_authorized()
