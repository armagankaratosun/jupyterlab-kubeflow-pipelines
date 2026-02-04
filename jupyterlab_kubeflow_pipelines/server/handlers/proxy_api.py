from __future__ import annotations

import json

import tornado.httpclient
from jupyter_server.base.handlers import APIHandler
from tornado import web

from ...config import get_config
from ..common import base_kfp_endpoint


class KfpProxyHandler(APIHandler):
    """Transparent proxy to KFP v2beta1 API (namespaced under /proxy/...)."""

    def get_kfp_url(self, path: str) -> str:
        cfg = get_config(self)
        return f"{base_kfp_endpoint(cfg.endpoint)}/apis/v2beta1/{path}"

    async def _proxy(self, *, method: str, path: str) -> None:
        self.log.info(f"KFP Proxy {method}: {path}")
        try:
            kfp_url = self.get_kfp_url(path)
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"error": str(e)}))
            return

        if self.request.query:
            kfp_url += f"?{self.request.query}"

        # Preserve client headers (including cookies) so Dex/IAP-style auth continues to work,
        # but drop Host to avoid upstream rejection.
        headers: dict[str, str] = dict(self.request.headers)
        headers.pop("Host", None)

        cfg = get_config(self)
        if cfg.token:
            headers["Authorization"] = f"Bearer {cfg.token}"

        body = None
        allow_nonstandard_methods = False
        if method in {"POST", "PUT", "PATCH"}:
            body = self.request.body or b""
        elif method == "DELETE":
            # Tornado disallows body for DELETE unless allow_nonstandard_methods=True.
            # KFP v2beta1 delete endpoints don't require a body, so omit it by default.
            if self.request.body:
                body = self.request.body
                allow_nonstandard_methods = True

        client = tornado.httpclient.AsyncHTTPClient()
        response = await client.fetch(
            kfp_url,
            method=method,
            body=body,
            headers=headers,
            raise_error=False,
            allow_nonstandard_methods=allow_nonstandard_methods,
        )
        self.set_status(response.code)
        self.write(response.body)
        self.finish()

    @web.authenticated
    async def get(self, path: str) -> None:
        await self._proxy(method="GET", path=path)

    @web.authenticated
    async def post(self, path: str) -> None:
        await self._proxy(method="POST", path=path)

    @web.authenticated
    async def delete(self, path: str) -> None:
        await self._proxy(method="DELETE", path=path)

    @web.authenticated
    async def put(self, path: str) -> None:
        await self._proxy(method="PUT", path=path)

    @web.authenticated
    async def patch(self, path: str) -> None:
        await self._proxy(method="PATCH", path=path)
