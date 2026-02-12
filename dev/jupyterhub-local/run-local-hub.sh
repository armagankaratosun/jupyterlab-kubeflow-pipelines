#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-hub-local"
LOCAL_HUB_DIR="${ROOT_DIR}/dev/jupyterhub-local"
CHP_BIN="${LOCAL_HUB_DIR}/node_modules/.bin/configurable-http-proxy"
BOOTSTRAP="${LOCAL_HUB_BOOTSTRAP:-1}"
RESET_STATE="${LOCAL_HUB_RESET:-0}"
PREKILL="${LOCAL_HUB_PREKILL:-1}"
BIND_URL="${JUPYTERHUB_BIND_URL:-http://127.0.0.1:8100}"
HUB_BIND_URL="${JUPYTERHUB_HUB_BIND_URL:-http://127.0.0.1:8101}"
PROXY_API_URL="${JUPYTERHUB_PROXY_API_URL:-http://127.0.0.1:8102}"

extract_port() {
  local url="$1"
  echo "${url}" | sed -E 's#.*:([0-9]+).*#\1#'
}

BIND_PORT="$(extract_port "${BIND_URL}")"
HUB_PORT="$(extract_port "${HUB_BIND_URL}")"
PROXY_API_PORT="$(extract_port "${PROXY_API_URL}")"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "==> Creating local virtualenv at ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

if [[ "${RESET_STATE}" == "1" ]]; then
  echo "==> Resetting local JupyterHub state"
  rm -rf "${LOCAL_HUB_DIR}/.jupyterhub"
fi

if [[ "${PREKILL}" == "1" ]]; then
  mapfile -t hub_pids < <(pgrep -f "jupyterhub -f ${ROOT_DIR}/dev/jupyterhub-local/jupyterhub_config.py" || true)
  for pid in "${hub_pids[@]}"; do
    echo "==> Stopping existing local Hub process (pid ${pid})"
    kill "${pid}" 2>/dev/null || true
  done
  if [[ "${#hub_pids[@]}" -gt 0 ]]; then
    sleep 1
  fi
fi

if [[ "${PREKILL}" == "1" ]] && command -v lsof >/dev/null 2>&1; then
  for port in "${BIND_PORT}" "${HUB_PORT}" "${PROXY_API_PORT}"; do
    mapfile -t pids < <(lsof -n -P -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)
    for pid in "${pids[@]}"; do
      cmd="$(ps -o command= -p "${pid}" 2>/dev/null || true)"
      if [[ "${cmd}" == *"configurable-http-proxy"* || "${cmd}" == *"jupyterhub"* ]]; then
        echo "==> Stopping stale listener on port ${port} (pid ${pid})"
        kill "${pid}" 2>/dev/null || true
      fi
    done
  done
  sleep 1

  # Grace period for orderly shutdown; if still occupied, force-stop known Hub/CHP processes.
  for _ in {1..10}; do
    busy=0
    for port in "${BIND_PORT}" "${HUB_PORT}" "${PROXY_API_PORT}"; do
      if lsof -n -P -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
        busy=1
      fi
    done
    [[ "${busy}" == "0" ]] && break
    sleep 0.5
  done

  for port in "${BIND_PORT}" "${HUB_PORT}" "${PROXY_API_PORT}"; do
    mapfile -t pids < <(lsof -n -P -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true)
    for pid in "${pids[@]}"; do
      cmd="$(ps -o command= -p "${pid}" 2>/dev/null || true)"
      if [[ "${cmd}" == *"configurable-http-proxy"* || "${cmd}" == *"jupyterhub"* ]]; then
        echo "==> Force-stopping stale listener on port ${port} (pid ${pid})"
        kill -9 "${pid}" 2>/dev/null || true
      fi
    done
  done
fi

if command -v lsof >/dev/null 2>&1; then
  for port in "${BIND_PORT}" "${HUB_PORT}" "${PROXY_API_PORT}"; do
    if lsof -n -P -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "ERROR: port ${port} is still in use. Set a different JUPYTERHUB_* URL or stop the process."
      exit 1
    fi
  done
fi

if [[ "${BOOTSTRAP}" == "1" ]]; then
  echo "==> Installing local Hub dependencies"
  python -m pip install --upgrade pip
  python -m pip install "jupyterhub>=5,<6" "jupyterlab>=4,<5"

  if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm is required to install configurable-http-proxy."
    exit 1
  fi

  if [[ ! -x "${CHP_BIN}" ]]; then
    echo "==> Installing configurable-http-proxy locally"
    npm install --prefix "${LOCAL_HUB_DIR}" --no-fund --no-audit configurable-http-proxy@^5
  fi

  echo "==> Installing this extension in editable mode"
  python -m pip install -e "${ROOT_DIR}"

  echo "==> Enabling server extension"
  jupyter server extension enable jupyterlab_kubeflow_pipelines
else
  echo "==> Skipping bootstrap (LOCAL_HUB_BOOTSTRAP=${BOOTSTRAP})"
fi

echo
echo "Local Hub will run at: ${BIND_URL}"
echo "Hub API will run at: ${HUB_BIND_URL}"
echo "Proxy API will run at: ${PROXY_API_URL}"
echo "Dummy login: any username, password: devpass"
echo "Set LOCAL_HUB_BOOTSTRAP=0 for fast restarts after first successful run."
echo "Press Ctrl+C to stop."
echo

export JUPYTERHUB_BIND_URL="${BIND_URL}"
export JUPYTERHUB_HUB_BIND_URL="${HUB_BIND_URL}"
export JUPYTERHUB_PROXY_API_URL="${PROXY_API_URL}"
export JUPYTERHUB_CHP_COMMAND="${CHP_BIN}"
exec jupyterhub -f "${ROOT_DIR}/dev/jupyterhub-local/jupyterhub_config.py"
