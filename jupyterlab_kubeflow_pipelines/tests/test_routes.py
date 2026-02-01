import json

import pytest
from tornado.httpclient import HTTPClientError


async def test_settings_default(jp_fetch):
    response = await jp_fetch("jupyterlab-kubeflow-pipelines", "settings")

    assert response.code == 200
    payload = json.loads(response.body)
    assert payload == {"endpoint": None, "namespace": "kubeflow", "has_token": False}


async def test_debug_requires_endpoint(jp_fetch):
    with pytest.raises(HTTPClientError) as exc_info:
        await jp_fetch("jupyterlab-kubeflow-pipelines", "debug")

    assert exc_info.value.code == 400
    payload = json.loads(exc_info.value.response.body)
    assert payload == {"error": "No endpoint configured"}
