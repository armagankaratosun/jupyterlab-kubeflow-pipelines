from __future__ import annotations

from tornado import web

from .proxy_ui import KfpUIProxyHandler


class KfpRootProxyHandler(KfpUIProxyHandler):
    """
    Special handler for gRPC/system calls that KFP UI hits at the root.

    It preserves the full path by calculating it from the request route.
    """

    @web.authenticated
    async def get(self, *args) -> None:
        await self._handle_root()

    @web.authenticated
    async def post(self, *args) -> None:
        await self._handle_root()

    @web.authenticated
    async def put(self, *args) -> None:
        await self._handle_root()

    @web.authenticated
    async def patch(self, *args) -> None:
        await self._handle_root()

    @web.authenticated
    async def delete(self, *args) -> None:
        await self._handle_root()

    @web.authenticated
    async def options(self, *args) -> None:
        await self._handle_root()

    @web.authenticated
    async def head(self, *args) -> None:
        await self._handle_root()

    async def _handle_root(self) -> None:
        base_url = self.settings.get("base_url", "/")
        path = self.request.path
        if path.startswith(base_url):
            path = path[len(base_url) :]
        path = path.lstrip("/")
        await self._proxy(path)
