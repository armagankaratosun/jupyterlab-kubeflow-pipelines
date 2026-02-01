from __future__ import annotations

import json

import tornado.httpclient
from jupyter_server.base.handlers import APIHandler
from tornado import web

from ...config import get_config
from ..common import base_kfp_endpoint


class KfpRunHandler(APIHandler):
    @web.authenticated
    async def get(self, run_id: str) -> None:
        cfg = get_config(self)
        try:
            kfp_endpoint = base_kfp_endpoint(cfg.endpoint)
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"error": str(e)}))
            return

        url = f"{kfp_endpoint}/apis/v2beta1/runs/{run_id}"
        headers: dict[str, str] = {}
        if cfg.token:
            headers["Authorization"] = f"Bearer {cfg.token}"

        client = tornado.httpclient.AsyncHTTPClient()
        response = await client.fetch(
            url, method="GET", headers=headers, raise_error=False
        )
        self.set_status(response.code)
        self.write(response.body)


class KfpRunTerminateHandler(APIHandler):
    @web.authenticated
    async def post(self, run_id: str) -> None:
        cfg = get_config(self)
        try:
            kfp_endpoint = base_kfp_endpoint(cfg.endpoint)
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"error": str(e)}))
            return

        url = f"{kfp_endpoint}/apis/v2beta1/runs/{run_id}:terminate"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if cfg.token:
            headers["Authorization"] = f"Bearer {cfg.token}"

        client = tornado.httpclient.AsyncHTTPClient()
        response = await client.fetch(
            url, method="POST", headers=headers, body=b"{}", raise_error=False
        )
        self.set_status(response.code)
        self.write(response.body or json.dumps({"status": "ok", "run_id": run_id}))
