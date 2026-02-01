from __future__ import annotations

import json
import time

import tornado.httpclient
from jupyter_server.base.handlers import APIHandler
from tornado import web

from ...config import get_config, get_public_config


class KfpDebugHandler(APIHandler):
    """Diagnostic handler to check backend connectivity to KFP."""

    @web.authenticated
    async def get(self) -> None:
        cfg = get_config(self)
        if not cfg.endpoint:
            self.set_status(400)
            self.write(json.dumps({"error": "No endpoint configured"}))
            return

        endpoint_to_test = cfg.endpoint.rstrip("/")
        if not endpoint_to_test.startswith("http"):
            endpoint_to_test = f"http://{endpoint_to_test}"

        client = tornado.httpclient.AsyncHTTPClient()
        result: dict[str, object] = {
            "config": get_public_config(self),
            "test_endpoint": endpoint_to_test,
        }

        try:
            start = time.monotonic()
            test_url = f"{endpoint_to_test}/apis/v2beta1/healthz"
            headers: dict[str, str] = {}
            if cfg.token:
                headers["Authorization"] = f"Bearer {cfg.token}"
            response = await client.fetch(
                test_url, request_timeout=5.0, headers=headers
            )
            result["connectivity"] = "SUCCESS"
            result["latency_ms"] = (time.monotonic() - start) * 1000
            result["status_code"] = response.code
            result["body"] = response.body.decode("utf-8")[:200]
        except Exception as e:
            result["connectivity"] = "FAILED"
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            self.set_status(502)

        self.write(json.dumps(result))
