from __future__ import annotations

from jupyter_server.utils import url_path_join

from ..kfp_compiler import (
    KfpCompileHandler,
    KfpSubmitHandler,
)
from ..kfp_pipelines import KfpImportPipelineHandler
from .handlers import (
    KfpDebugHandler,
    KfpProxyHandler,
    KfpRootProxyHandler,
    KfpRunHandler,
    KfpRunTerminateHandler,
    KfpSettingsHandler,
    KfpUIProxyHandler,
)


def setup_handlers(web_app) -> None:
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]

    api_proxy_route = url_path_join(
        base_url, "jupyterlab-kubeflow-pipelines", "proxy", "(.*)"
    )
    compile_route = url_path_join(
        base_url, "jupyterlab-kubeflow-pipelines", "kfp", "compile"
    )
    submit_route = url_path_join(
        base_url, "jupyterlab-kubeflow-pipelines", "kfp", "submit"
    )
    import_pipeline_route = url_path_join(
        base_url, "jupyterlab-kubeflow-pipelines", "kfp", "pipelines", "import"
    )
    kfp_ui_route = url_path_join(base_url, "kfp-ui", "(.*)")
    settings_route = url_path_join(
        base_url, "jupyterlab-kubeflow-pipelines", "settings"
    )
    run_route = url_path_join(base_url, "jupyterlab-kubeflow-pipelines", "runs", "(.*)")
    run_terminate_route = url_path_join(
        base_url, "jupyterlab-kubeflow-pipelines", "runs", "(.*):terminate"
    )
    debug_route = url_path_join(base_url, "jupyterlab-kubeflow-pipelines", "debug")

    handlers = [
        (settings_route, KfpSettingsHandler),
        (api_proxy_route, KfpProxyHandler),
        (kfp_ui_route, KfpUIProxyHandler),
        (compile_route, KfpCompileHandler),
        (submit_route, KfpSubmitHandler),
        (import_pipeline_route, KfpImportPipelineHandler),
        (run_terminate_route, KfpRunTerminateHandler),
        (run_route, KfpRunHandler),
        (
            url_path_join(base_url, "ml_metadata.MetadataStoreService/.*"),
            KfpRootProxyHandler,
        ),
        (url_path_join(base_url, "system/.*"), KfpRootProxyHandler),
        (url_path_join(base_url, "apis/v1beta1/.*"), KfpRootProxyHandler),
        (url_path_join(base_url, "apis/v2beta1/.*"), KfpRootProxyHandler),
        (debug_route, KfpDebugHandler),
    ]

    # JupyterHub path-based deployments mount the user server under base_url
    # (e.g. /user/<name>/). The embedded KFP UI issues root-relative requests like
    # /ml_metadata.MetadataStoreService/... which bypass base_url. When JupyterHub
    # is using subdomains, those requests still reach the single-user server but
    # will 403 unless we also register root-level handlers.
    if base_url != "/":
        handlers.extend(
            [
                (r"/ml_metadata.MetadataStoreService/.*", KfpRootProxyHandler),
                (r"/system/.*", KfpRootProxyHandler),
                (r"/apis/v1beta1/.*", KfpRootProxyHandler),
                (r"/apis/v2beta1/.*", KfpRootProxyHandler),
            ]
        )

    web_app.add_handlers(host_pattern, handlers)
