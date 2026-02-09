from __future__ import annotations

from jupyter_server.utils import url_path_join
from tornado.web import RequestHandler


class BaseUrlRedirectHandler(RequestHandler):
    """
    Redirect root-relative requests to the Jupyter Server base_url.

    Some embedded UIs (notably KFP UI) issue root-relative requests like
    `/ml_metadata.MetadataStoreService/...` even when Jupyter Server is mounted
    under a base_url (e.g. `/user/<name>/` on JupyterHub).

    When auth cookies are path-scoped to base_url, those root requests arrive
    unauthenticated and may 403. A 307 redirect moves the request under base_url
    while preserving method/body (important for gRPC-web POSTs).
    """

    def initialize(self, *, base_url: str) -> None:  # type: ignore[override]
        self._base_url = base_url

    def check_xsrf_cookie(self) -> None:
        # We only redirect; the target handler will enforce auth/XSRF as needed.
        return

    def _redirect(self) -> None:
        if not self._base_url or self._base_url == "/":
            self.set_status(404)
            self.finish()
            return

        path = self.request.path.lstrip("/")
        target = url_path_join(self._base_url, path)
        if self.request.query:
            target = f"{target}?{self.request.query}"

        self.set_status(307)
        self.set_header("Location", target)
        self.set_header("Cache-Control", "no-store")
        self.finish()

    def get(self) -> None:
        self._redirect()

    def post(self) -> None:
        self._redirect()

    def put(self) -> None:
        self._redirect()

    def patch(self) -> None:
        self._redirect()

    def delete(self) -> None:
        self._redirect()

    def head(self) -> None:
        self._redirect()

    def options(self) -> None:
        self._redirect()
