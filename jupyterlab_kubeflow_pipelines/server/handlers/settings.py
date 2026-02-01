from __future__ import annotations

import json

from jupyter_server.base.handlers import APIHandler
from tornado import web

from ...config import (
    _UNSET,
    get_public_config,
    update_config,
)


class KfpSettingsHandler(APIHandler):
    """Get/set KFP configuration in the backend."""

    @web.authenticated
    def get(self) -> None:
        self.write(json.dumps(get_public_config(self)))

    @web.authenticated
    def post(self) -> None:
        input_data = self.get_json_body()
        token = input_data["token"] if "token" in input_data else _UNSET
        try:
            cfg = update_config(
                self,
                endpoint=input_data.get("endpoint"),
                namespace=input_data.get("namespace"),
                token=token,
            )
        except ValueError as e:
            self.set_status(400)
            self.write(json.dumps({"error": str(e)}))
            return

        self.log.info(f"KFP Config Updated: endpoint={cfg.endpoint}")
        self.write(json.dumps({"status": "success", "config": get_public_config(self)}))
