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
    KfpRootFallbackProxyHandler,
    KfpRunHandler,
    KfpRunTerminateHandler,
    KfpSettingsHandler,
    KfpUIProxyHandler,
    KfpUIPathRewriteScriptHandler,
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
    kfp_ui_rewrite_script_route = url_path_join(base_url, "kfp-ui", "_jlkfp_path_rewrite.js")
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
        (kfp_ui_rewrite_script_route, KfpUIPathRewriteScriptHandler),
        (kfp_ui_route, KfpUIProxyHandler),
        (compile_route, KfpCompileHandler),
        (submit_route, KfpSubmitHandler),
        (import_pipeline_route, KfpImportPipelineHandler),
        (run_terminate_route, KfpRunTerminateHandler),
        (run_route, KfpRunHandler),
        (debug_route, KfpDebugHandler),
    ]

    handlers.extend(
        [
            (
                r"/ml_metadata.MetadataStoreService/.*",
                KfpRootFallbackProxyHandler,
                {"base_url": base_url},
            ),
            (r"/system/.*", KfpRootFallbackProxyHandler, {"base_url": base_url}),
            (r"/apis/v1beta1/.*", KfpRootFallbackProxyHandler, {"base_url": base_url}),
            (r"/apis/v2beta1/.*", KfpRootFallbackProxyHandler, {"base_url": base_url}),
            (r"/k8s/.*", KfpRootFallbackProxyHandler, {"base_url": base_url}),
        ]
    )

    web_app.add_handlers(host_pattern, handlers)
