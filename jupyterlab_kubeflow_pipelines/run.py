from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Run:
    run_id: str
    label: str | None = None
    _kfp_client: Any | None = field(default=None, repr=False, compare=False)

    def open_ui(self) -> None:
        """
        Ask the JupyterLab extension to open the run details view.
        """
        try:
            from IPython.display import Javascript, display
        except ImportError:
            raise RuntimeError(
                "IPython is required to open the run UI from a notebook."
            )

        label_js = f"'{self.label}'" if self.label else "undefined"
        display(
            Javascript(
                f"""
                (function() {{
                  window.top.postMessage({{
                    type: 'kfp-open-run',
                    runId: '{self.run_id}',
                    label: {label_js}
                  }}, '*');
                }})();
                """
            )
        )

    def status(self) -> dict[str, Any]:
        """
        Return a small, stable status dict for this run.

        Uses the KFP Python SDK if this Run was created with a client attached.
        """
        if self._kfp_client is None:
            raise RuntimeError(
                "Run.status() is not available because no KFP client is attached. "
                "Create runs via KFPClient.create_run_from_*() to enable status()/wait()."
            )

        run = self._kfp_client.get_run(self.run_id)
        return {
            "run_id": self.run_id,
            "display_name": getattr(run, "display_name", None),
            "state": getattr(run, "state", None),
            "created_at": getattr(run, "created_at", None),
        }

    def wait(self, *, timeout: int = 3600, poll_interval: int = 5) -> dict[str, Any]:
        """
        Block until the run completes (or timeout).

        `timeout` is required by the KFP SDK and is expressed in seconds.
        """
        if self._kfp_client is None:
            raise RuntimeError(
                "Run.wait() is not available because no KFP client is attached. "
                "Create runs via KFPClient.create_run_from_*() to enable status()/wait()."
            )

        run = self._kfp_client.wait_for_run_completion(
            run_id=self.run_id,
            timeout=timeout,
            sleep_duration=poll_interval,
        )
        return {
            "run_id": self.run_id,
            "display_name": getattr(run, "display_name", None),
            "state": getattr(run, "state", None),
        }

    def watch(
        self,
        *,
        poll_interval: int = 2,
        timeout: int | None = None,
        print_initial: bool = True,
    ) -> dict[str, Any]:
        """
        Poll run status and print state transitions until completion (or timeout).

        This is a lightweight helper for notebook interactivity (no logs/artifacts).
        """
        if self._kfp_client is None:
            raise RuntimeError(
                "Run.watch() is not available because no KFP client is attached. "
                "Create runs via KFPClient.create_run_from_*() to enable status()/wait()/watch()."
            )

        terminal_states = {
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
            "SKIPPED",
            "ERROR",
        }

        start = time.monotonic()
        last_state: str | None = None
        last_printed = False

        while True:
            info = self.status()
            state = info.get("state")

            if print_initial and not last_printed:
                print(f"[kfp] run_id={self.run_id} state={state}")
                last_printed = True
                last_state = state
            elif state != last_state:
                elapsed = int(time.monotonic() - start)
                print(f"[kfp] +{elapsed}s state={state}")
                last_state = state

            if state in terminal_states:
                return info

            if timeout is not None and (time.monotonic() - start) >= timeout:
                raise TimeoutError(
                    f"Run {self.run_id} did not complete within {timeout} seconds."
                )

            time.sleep(max(0.1, poll_interval))

    def terminate(self) -> None:
        """
        Ask the JupyterLab extension to terminate the run.

        This avoids requiring the notebook kernel to have KFP credentials; the browser
        performs an authenticated call to the server extension.
        """
        try:
            from IPython.display import Javascript, display
        except ImportError:
            raise RuntimeError("IPython is required to terminate runs from a notebook.")

        display(
            Javascript(
                f"""
                (function() {{
                  window.top.postMessage({{
                    type: 'kfp-terminate-run',
                    runId: '{self.run_id}'
                  }}, '*');
                }})();
                """
            )
        )
