# JupyterLab Kubeflow Pipelines

[![Github Actions Status](https://github.com/armagankaratosun/jupyterlab-kubeflow-pipelines/workflows/Build/badge.svg)](https://github.com/armagankaratosun/jupyterlab-kubeflow-pipelines/actions/workflows/build.yml)

JupyterLab extension to visualize Kubeflow Pipelines v2.

## Requirements

- JupyterLab >= 4.0.0

## Install

To install the extension, execute:

```bash
pip install jupyterlab-kubeflow-pipelines
```

## Uninstall

To remove the extension, execute:

```bash
pip uninstall jupyterlab-kubeflow-pipelines
```

## Troubleshoot

If you are seeing the frontend extension, but it is not working, check
that the server extension is enabled:

```bash
jupyter server extension list
```

If the server extension is installed and enabled, but you are not seeing
the frontend extension, check the frontend extension is installed:

```bash
jupyter labextension list
```

### NetworkPolicy requirements

In Kubernetes deployments, ensure notebook/hub pods can reach both Kubeflow
Pipelines API and UI backends. This applies to both standalone KFP and
Kubeflow Platform setups.

- API backend: `ml-pipeline` (commonly port `8888`)
- UI backend: `ml-pipeline-ui` (commonly service port `80` -> pod port `3000`)

If cross-namespace traffic is restricted, allow ingress from your profile/user
namespaces to the `ml-pipeline` and `ml-pipeline-ui` pods/services.

### JupyterHub + embedded KFP UI

Kubeflow Pipelines UI issues root-relative calls (for example
`/ml_metadata.MetadataStoreService/...`) even when Jupyter is mounted under a
base URL such as `/user/<name>/`.

In a path-based JupyterHub deployment, those requests would otherwise go to the
Hub at `/<...>` (not the single-user server at `/<base_url>/...`), and commonly
fail with `403` (XSRF) errors.

This extension addresses that by injecting a small, scoped runtime URL rewriter
into the proxied KFP UI _shell HTML_ only (no Hub config changes required). The
rewriter ensures root-relative KFP API calls stay under the user server path:

- `/ml_metadata.MetadataStoreService/...` -> `/<base_url>/kfp-ui/ml_metadata.MetadataStoreService/...`
- `/system/...` -> `/<base_url>/kfp-ui/system/...`
- `/apis/v1beta1/...`, `/apis/v2beta1/...` -> `/<base_url>/kfp-ui/apis/...`
- `/k8s/...` -> `/<base_url>/kfp-ui/k8s/...`

To stay compatible with stricter Content-Security-Policy setups, the injected
tag loads the rewriter from `/<base_url>/kfp-ui/_jlkfp_path_rewrite.js`.

### Local JupyterHub Repro Harness

To reproduce Hub-specific routing behavior quickly on a laptop:

```bash
bash dev/jupyterhub-local/run-local-hub.sh
```

Notes:

- The helper creates a local venv at `.venv-hub-local`.
- It runs JupyterHub on `http://127.0.0.1:8100`.
- Hub internal API defaults to `http://127.0.0.1:8102` to avoid common local port conflicts.
- Dummy login is enabled (`password: devpass`, username can be any value).
- The helper installs `configurable-http-proxy` locally under `dev/jupyterhub-local/node_modules`.
- After first setup, use `LOCAL_HUB_BOOTSTRAP=0 bash dev/jupyterhub-local/run-local-hub.sh` for fast restarts.
- If you hit redirect loops, start with `LOCAL_HUB_RESET=1 LOCAL_HUB_BOOTSTRAP=0 bash dev/jupyterhub-local/run-local-hub.sh`.
- The helper pre-cleans stale local `jupyterhub`/`configurable-http-proxy` listeners on Hub/proxy ports.
- The helper also terminates older runs started with the same local config before launching.

## Contributing

### Development install

Note: You will need NodeJS to build the extension package.

The `jlpm` command is JupyterLab's pinned version of
[yarn](https://yarnpkg.com/) that is installed with JupyterLab. You may use
`yarn` or `npm` in lieu of `jlpm` below.

```bash
# Clone the repo to your local environment
# Change directory to the jupyterlab_kubeflow_pipelines directory

# Set up a virtual environment and install package in development mode
uv venv --python 3.12
source .venv/bin/activate
uv pip install --editable ".[dev,test]"

# Link your development version of the extension with JupyterLab
jupyter labextension develop . --overwrite
# Server extension must be manually installed in develop mode
jupyter server extension enable jupyterlab_kubeflow_pipelines

# Rebuild extension Typescript source after making changes
# IMPORTANT: Unlike the steps above which are performed only once, do this step
# every time you make a change.
jlpm build
```

You can watch the source directory and run JupyterLab at the same time in different terminals to watch for changes in the extension's source and automatically rebuild the extension.

```bash
# Watch the source directory in one terminal, automatically rebuilding when needed
jlpm watch
# Run JupyterLab in another terminal
jupyter lab
```

With the watch command running, every saved change will immediately be built locally and available in your running JupyterLab. Refresh JupyterLab to load the change in your browser (you may need to wait several seconds for the extension to be rebuilt).

By default, the `jlpm build` command generates the source maps for this extension to make it easier to debug using the browser dev tools. To also generate source maps for the JupyterLab core extensions, you can run the following command:

```bash
jupyter lab build --minimize=False
```

### Development uninstall

```bash
# Server extension must be manually disabled in develop mode
jupyter server extension disable jupyterlab_kubeflow_pipelines
pip uninstall jupyterlab-kubeflow-pipelines
```

In development mode, you will also need to remove the symlink created by `jupyter labextension develop`
command. To find its location, you can run `jupyter labextension list` to figure out where the `labextensions`
folder is located. Then you can remove the symlink named `jupyterlab-kubeflow-pipelines` within that folder.

### Testing the extension

#### Server tests

This extension is using [Pytest](https://docs.pytest.org/) for Python code testing.

Install test dependencies (needed only once):

```sh
uv pip install -e ".[test]"
# Each time you install the Python package, you need to restore the front-end extension link
jupyter labextension develop . --overwrite
```

To execute them, run:

```sh
pytest -vv -r ap --cov jupyterlab_kubeflow_pipelines
```

#### Frontend tests

This extension is using [Jest](https://jestjs.io/) for JavaScript code testing.

To execute them, execute:

```sh
jlpm
jlpm test
```

#### Integration tests

This extension uses [Playwright](https://playwright.dev/docs/intro) for the integration tests (aka user level tests).
More precisely, the JupyterLab helper [Galata](https://github.com/jupyterlab/jupyterlab/tree/master/galata) is used to handle testing the extension in JupyterLab.

More information are provided within the [ui-tests](./ui-tests/README.md) README.

## AI Coding Assistant Support

This project includes an `AGENTS.md` file with coding standards and best practices for JupyterLab extension development. The file follows the [AGENTS.md standard](https://agents.md) for cross-tool compatibility.

### Compatible AI Tools

`AGENTS.md` works with AI coding assistants that support the standard, including Cursor, GitHub Copilot, Windsurf, Aider, and others. For a current list of compatible tools, see [the AGENTS.md standard](https://agents.md).
This project also includes symlinks for tool-specific compatibility:

- `CLAUDE.md` → `AGENTS.md` (for Claude Code)

- `GEMINI.md` → `AGENTS.md` (for Gemini Code Assist)

Other conventions you might encounter:

- `.cursorrules` - Cursor's YAML/JSON format (Cursor also supports AGENTS.md natively)
- `CONVENTIONS.md` / `CONTRIBUTING.md` - For CodeConventions.ai and GitHub bots
- Project-specific rules in JetBrains AI Assistant settings

All tool-specific files should be symlinks to `AGENTS.md` as the single source of truth.

### What's Included

The `AGENTS.md` file provides guidance on:

- Code quality rules and file-scoped validation commands
- Naming conventions for packages, plugins, and files
- Coding standards (TypeScript, Python)
- Development workflow and debugging
- Backend-frontend integration patterns (`APIHandler`, `requestAPI()`, routing)
- Common pitfalls and how to avoid them

### Customization

You can edit `AGENTS.md` to add project-specific conventions or adjust guidelines to match your team's practices. The file uses plain Markdown with Do/Don't patterns and references to actual project files.

**Note**: `AGENTS.md` is living documentation. Update it when you change conventions, add dependencies, or discover new patterns. Include `AGENTS.md` updates in commits that modify workflows or coding standards.

### Packaging the extension

See [RELEASE](RELEASE.md)
