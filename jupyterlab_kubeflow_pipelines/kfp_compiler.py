import importlib.util
import inspect
import json
import os
import sys
import tempfile
import traceback
from urllib.parse import urlparse

from jupyter_server.base.handlers import APIHandler
from kfp.compiler import Compiler
from tornado import web

from .config import get_config


def _normalize_kfp_host(endpoint: str) -> str:
    endpoint = (endpoint or "").strip()
    if not endpoint:
        raise ValueError("KFP endpoint is empty.")

    if "://" not in endpoint:
        endpoint = f"http://{endpoint}"

    parsed = urlparse(endpoint)
    if not parsed.netloc:
        raise ValueError(f"Invalid KFP endpoint: {endpoint!r}")

    hostname = parsed.hostname or ""
    if parsed.port is None and hostname in {"localhost", "127.0.0.1"}:
        raise ValueError(
            f"KFP endpoint {endpoint!r} has no port. Did you mean 'http://{hostname}:8080'?"
        )

    # The KFP SDK host should be the origin (scheme://netloc) without path/query/fragment.
    return f"{parsed.scheme}://{parsed.netloc}"


class KfpCompileHandler(APIHandler):
    """
    Handler to compile KFP pipelines from source code.
    Receives python source code, executes it, finds pipeline functions,
    and returns their metadata or compiled YAML.
    """

    @web.authenticated
    async def post(self):
        try:
            body = json.loads(self.request.body)
            action = body.get("action", "inspect")  # 'inspect' or 'compile'
            source_code = body.get("source_code", "")
            pipeline_name = body.get("pipeline_name", None)

            if not source_code:
                self.set_status(400)
                self.write(json.dumps({"error": "No source_code provided"}))
                return

            # Execute the code in a temporary context to find pipelines
            pipelines = self._find_pipelines(source_code)

            if not pipelines:
                self.write(
                    json.dumps(
                        {
                            "pipelines": [],
                            "error": "No @dsl.pipeline decorated functions found in the provided code.",
                        }
                    )
                )
                return

            if action == "inspect":
                # Return list of detected pipelines and their arguments
                self.write(
                    json.dumps(
                        {
                            "pipelines": [
                                {
                                    "name": p["name"],
                                    "display_name": p["display_name"],
                                    "description": p["description"],
                                    "args": p["args"],
                                }
                                for p in pipelines
                            ]
                        }
                    )
                )

            elif action == "compile":
                if not pipeline_name:
                    # Default to the first found pipeline
                    target_pipeline = pipelines[0]
                else:
                    target_pipeline = next(
                        (p for p in pipelines if p["name"] == pipeline_name), None
                    )

                if not target_pipeline:
                    self.set_status(404)
                    self.write(
                        json.dumps({"error": f"Pipeline '{pipeline_name}' not found."})
                    )
                    return

                # Compile to YAML
                with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
                    package_path = tmp.name

                try:
                    Compiler().compile(
                        pipeline_func=target_pipeline["func"], package_path=package_path
                    )

                    with open(package_path) as f:
                        yaml_content = f.read()

                    self.write(
                        json.dumps(
                            {
                                "status": "compiled",
                                "pipeline_name": target_pipeline["name"],
                                "package_path": package_path,
                                "yaml": yaml_content,
                            }
                        )
                    )
                except Exception:
                    # Cleanup on error
                    if os.path.exists(package_path):
                        os.unlink(package_path)
                    raise

        except Exception as e:
            self.log.error(f"Compilation error: {traceback.format_exc()}")
            self.set_status(500)
            self.write(
                json.dumps({"error": str(e), "traceback": traceback.format_exc()})
            )

    def _sanitize_source_code(self, source_code: str) -> str:
        """
        Sanitizes notebook source code by commenting out IPython magics
        and other non-Python syntax to make it executable by pure Python.
        """
        lines = source_code.splitlines()
        sanitized = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("!", "%")):
                sanitized.append("# " + line)  # Comment out magics
            else:
                sanitized.append(line)

        # Add mock get_ipython to global scope if needed
        # We need to make sure get_ipython is available during execution
        mock_ipython = "\n# Mock get_ipython for compatibility\nif 'get_ipython' not in globals():\n    get_ipython = lambda: None\n"
        return "\n".join(sanitized) + mock_ipython

    def _find_pipelines(self, source_code):
        """
        Executes source code string and returns list of KFP pipeline objects.
        Writes code to a temp file so that inspect.getsource works (required by KFP).
        """
        pipelines = []

        # Sanitize code first
        source_code = self._sanitize_source_code(source_code)

        # Create a temporary file
        # We use a unique name but keep .py extension
        import uuid

        module_name = f"kfp_temp_{uuid.uuid4().hex}"

        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False
        ) as tmp_file:
            tmp_file.write(source_code)
            tmp_path = tmp_file.name

        try:
            # Load the file as a module
            spec = importlib.util.spec_from_file_location(module_name, tmp_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)
                except Exception as e:
                    self.log.warning(f"Partial execution failure in notebook code: {e}")

                # Inspect module for functions decorated with @dsl.pipeline
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) or hasattr(obj, "__call__"):
                        is_pipeline = False

                        # Check for KFP v2 GraphComponent (Pipeline)
                        # Distinguish from PythonComponent by checking implementation type (Graph vs Container)
                        if hasattr(obj, "component_spec") and hasattr(
                            obj.component_spec, "implementation"
                        ):
                            impl = obj.component_spec.implementation
                            # Only pipelines have a graph implementation
                            if getattr(impl, "graph", None) is not None:
                                is_pipeline = True

                        # Legacy/V1 checks or fallback
                        if not is_pipeline:
                            if getattr(obj, "_is_pipeline", False):
                                is_pipeline = True

                        if is_pipeline:
                            # Extract arguments using inspect
                            sig = inspect.signature(obj)
                            args = []
                            for param_name, param in sig.parameters.items():
                                args.append(
                                    {
                                        "name": param_name,
                                        "default": str(param.default)
                                        if param.default != inspect.Parameter.empty
                                        else None,
                                        "type": str(param.annotation.__name__)
                                        if hasattr(param.annotation, "__name__")
                                        else str(param.annotation),
                                    }
                                )

                            # Try to extract the KFP display name
                            display_name = name
                            if hasattr(obj, "pipeline_spec") and hasattr(
                                obj.pipeline_spec, "pipeline_info"
                            ):
                                display_name = obj.pipeline_spec.pipeline_info.name
                            elif hasattr(obj, "component_spec") and getattr(
                                obj.component_spec, "name", None
                            ):
                                display_name = obj.component_spec.name

                            pipelines.append(
                                {
                                    "name": name,
                                    "display_name": display_name,
                                    "description": obj.__doc__,
                                    "args": args,
                                    "func": obj,
                                }
                            )

        except Exception as e:
            self.log.error(f"Error inspecting source code: {e}")
            raise
        finally:
            # Cleanup
            if module_name in sys.modules:
                del sys.modules[module_name]
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        return pipelines


class KfpSubmitHandler(APIHandler):
    """
    Handler to submit a compiled pipeline to the KFP backend.
    """

    @web.authenticated
    async def post(self):
        try:
            body = json.loads(self.request.body)
            pipeline_package_path = body.get("package_path")  # Path to local YAML
            pipeline_yaml = body.get("pipeline_yaml")  # Or direct YAML content
            run_name = body.get("run_name", "Notebook Run")
            experiment_id = body.get("experiment_id", None)
            params = body.get("params", {})

            cfg = get_config(self)
            if not cfg.endpoint:
                self.set_status(400)
                self.write(
                    json.dumps(
                        {
                            "error": "KFP endpoint is not configured. Set it in the extension settings first."
                        }
                    )
                )
                return

            if not pipeline_yaml and not pipeline_package_path:
                self.set_status(400)
                self.write(
                    json.dumps({"error": "No pipeline_yaml or package_path provided"})
                )
                return

            # Ensure we have a file to submit
            local_file = None
            if pipeline_yaml:
                import tempfile

                with tempfile.NamedTemporaryFile(
                    suffix=".yaml", delete=False, mode="w"
                ) as tmp:
                    tmp.write(pipeline_yaml)
                    local_file = tmp.name
            else:
                local_file = pipeline_package_path

            if not os.path.exists(local_file):
                self.set_status(400)
                self.write(
                    json.dumps({"error": f"Pipeline file not found: {local_file}"})
                )
                return

            # Initialize KFP Client
            # Note: We need to handle auth. For now assuming Bearer token if provided.
            import kfp

            try:
                host = _normalize_kfp_host(cfg.endpoint)
            except ValueError as e:
                self.set_status(400)
                self.write(json.dumps({"error": str(e)}))
                return

            client_args = {"host": host}
            if cfg.token:
                # KFP client supports 'existing_token' or we can set headers manually
                # For v2, headers are often passed differently.
                # Simplest is to use the cookies or existing session if running in-cluster,
                # but for external/proxy access, we might need to inject headers.
                # Monkey-patching or using specific client features might be needed.
                # For now, let's try standard client instantiation.
                client_args["existing_token"] = cfg.token

            # TODO: Improve auth handling for various KFP setups (IAP, Dex, etc)
            try:
                client = kfp.Client(**client_args)
            except Exception as e:
                self.set_status(502)
                self.write(
                    json.dumps(
                        {
                            "error": "Failed to connect to Kubeflow Pipelines.",
                            "detail": str(e),
                            "endpoint": cfg.endpoint,
                            "normalized_host": host,
                        }
                    )
                )
                return

            try:
                # Submit run
                # usage: create_run_from_pipeline_package(pipeline_file, arguments, run_name, experiment_name/id...)
                # Check if experiment_name needed
                experiment_name = None
                if experiment_id:
                    try:
                        exp = client.get_experiment(experiment_id=experiment_id)
                        experiment_name = exp.name
                    except Exception:
                        pass  # Fallback to default or let client handle it

                run_result = client.create_run_from_pipeline_package(
                    pipeline_file=local_file,
                    arguments=params,
                    run_name=run_name,
                    experiment_name=experiment_name,
                    enable_caching=True,
                )

                self.write(
                    json.dumps(
                        {
                            "run_id": run_result.run_id,
                            "run_name": run_name,
                            "url": f"{host}/#/runs/details/{run_result.run_id}",
                        }
                    )
                )

            finally:
                # Cleanup temp file
                if local_file and os.path.exists(local_file):
                    try:
                        os.unlink(local_file)
                    except Exception:
                        pass

        except Exception as e:
            self.log.error(f"Submission error: {traceback.format_exc()}")
            self.set_status(500)
            self.write(
                json.dumps({"error": str(e), "traceback": traceback.format_exc()})
            )
