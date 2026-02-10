from __future__ import annotations

import json
import time

import tornado.httpclient
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.utils import url_path_join
from tornado import web

from ...config import get_config
from ..common import base_kfp_endpoint

BRIDGE_COOKIE_NAME = "jlkfp-bridge-auth"
BRIDGE_COOKIE_TTL_SECONDS = 600


class KfpUIProxyHandler(JupyterHandler):
    """
    Proxy handler for embedding KFP UI in an iframe.

    Forwards requests to the KFP frontend using server-side config.
    """

    def check_xsrf_cookie(self) -> None:
        """Bypass XSRF check for the transparent proxy."""
        return

    def write_error(self, status_code: int, **kwargs) -> None:
        """
        Prevent Jupyter from serving HTML error pages for the proxy.
        If the proxy fails, we want the client to receive the raw status and body (if any),
        not a browser-unfriendly HTML error.
        """
        self.set_header("Content-Type", "application/json")
        if "exc_info" in kwargs:
            err = kwargs["exc_info"][1]
            self.finish(json.dumps({"error": str(err)}))
        else:
            self.finish(json.dumps({"error": f"HTTP {status_code}"}))

    def _set_bridge_cookie(self) -> None:
        """
        Mint a short-lived signed cookie scoped to this user server.

        Root-relative KFP UI calls (e.g. /ml_metadata.MetadataStoreService/*) do not
        always include JupyterHub's path-scoped auth cookies. This cookie allows our
        root handlers to authorize and proxy those calls without JS injection.
        """
        session_id = self.get_cookie("jupyterhub-session-id", default="") or ""
        payload = json.dumps(
            {
                "base_url": self.settings.get("base_url", "/"),
                "sid": session_id,
                "exp": int(time.time()) + BRIDGE_COOKIE_TTL_SECONDS,
            }
        )
        self.set_secure_cookie(
            BRIDGE_COOKIE_NAME,
            payload,
            path="/",
            httponly=True,
            secure=self.request.protocol == "https",
            samesite="Lax",
        )

    @web.authenticated
    async def get(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def post(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def put(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def patch(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def delete(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def options(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def head(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    async def _proxy(self, path: str) -> None:
        cfg = get_config(self)
        try:
            kfp_endpoint = base_kfp_endpoint(cfg.endpoint).rstrip("/")
        except ValueError as e:
            self.set_status(412)
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({"error": str(e)}))
            return

        kfp_url = f"{kfp_endpoint}/{path.lstrip('/')}"
        if self.request.query:
            kfp_url += f"?{self.request.query}"

        self.log.info(f"KFP Proxy Request: {self.request.method} {path} -> {kfp_url}")

        client = tornado.httpclient.AsyncHTTPClient()

        try:
            # Pass through all client headers except hop-by-hop ones and Host.
            # This maximizes compatibility with Dex/IAP and gRPC-Web stacks.
            hop_by_hop = {
                "host",
                "connection",
                "keep-alive",
                "proxy-authenticate",
                "proxy-authorization",
                "te",
                "trailers",
                "transfer-encoding",
                "upgrade",
            }
            headers: dict[str, str] = {
                h: v for h, v in self.request.headers.items() if h.lower() not in hop_by_hop
            }

            if cfg.token:
                headers["Authorization"] = f"Bearer {cfg.token}"

            request_body = None
            allow_nonstandard_methods = False
            if self.request.method in {"POST", "PUT", "PATCH"}:
                request_body = self.request.body or b""
            elif self.request.method == "DELETE":
                if self.request.body:
                    request_body = self.request.body
                    allow_nonstandard_methods = True

            response = await client.fetch(
                kfp_url,
                method=self.request.method,
                headers=headers,
                body=request_body,
                raise_error=False,
                follow_redirects=False,
                decompress_response=False,
                allow_nonstandard_methods=allow_nonstandard_methods,
                connect_timeout=15.0,
                request_timeout=60.0,
            )

            self.log.info(f"KFP Proxy Response: {response.code} for {path}")
            self.set_status(response.code)

            base_proxy_url = url_path_join(self.settings.get("base_url", "/"), "kfp-ui")

            for h, v in response.headers.items():
                l_h = h.lower()
                if l_h in [
                    "content-length",
                    "transfer-encoding",
                    "connection",
                    "set-cookie",
                    "server",
                ]:
                    continue

                if l_h == "location":
                    orig_loc = v
                    if orig_loc.startswith(kfp_endpoint):
                        new_loc = orig_loc.replace(
                            kfp_endpoint, base_proxy_url.rstrip("/"), 1
                        )
                    elif orig_loc.startswith("/"):
                        new_loc = url_path_join(base_proxy_url, orig_loc)
                    else:
                        new_loc = orig_loc
                    self.set_header("Location", new_loc)
                    continue

                self.set_header(h, v)

            self.set_header("X-Frame-Options", "SAMEORIGIN")
            self.set_header("Content-Security-Policy", "frame-ancestors 'self'")

            if path.endswith(".js"):
                self.set_header("Content-Type", "application/javascript")
            elif path.endswith(".css"):
                self.set_header("Content-Type", "text/css")

            if response.code != 304:
                self.write(response.body)

        except tornado.httpclient.HTTPClientError as e:
            # Typically connection refused / timeouts / TLS issues.
            self.log.error(f"UI Proxy HTTPClientError at {path}: {e}", exc_info=True)
            self.set_status(502)
            self.set_header("Content-Type", "application/json")
            self.write(
                json.dumps(
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "kfp_url": kfp_url,
                    }
                )
            )
        except Exception as e:
            self.log.error(f"UI Proxy Exception at {path}: {e}", exc_info=True)
            self.set_status(500)
            self.set_header("Content-Type", "application/json")
            self.write(
                json.dumps(
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "kfp_url": kfp_url,
                    }
                )
            )
