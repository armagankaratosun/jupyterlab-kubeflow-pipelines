from __future__ import annotations

import json
import time

import tornado.httpclient
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.utils import url_path_join
from tornado import web

from ...config import get_config
from ..common import base_kfp_endpoint

BRIDGE_COOKIE_NAME = "jlkfp-bridge-auth"
BRIDGE_COOKIE_TTL_SECONDS = 600
_RUNTIME_REWRITER_SENTINEL = "__KFP_PATH_REWRITE_INSTALLED__"


class KfpUIProxyHandler(JupyterHandler):
    """
    Proxy handler for embedding KFP UI in an iframe.

    Forwards requests to the KFP frontend using server-side config.
    """

    def check_xsrf_cookie(self) -> None:
        """Bypass XSRF check for the transparent proxy."""
        return

    def write_error(self, status_code: int, **kwargs) -> None:
        """
        Prevent Jupyter from serving HTML error pages for the proxy.
        If the proxy fails, we want the client to receive the raw status and body (if any),
        not a browser-unfriendly HTML error.
        """
        self.set_header("Content-Type", "application/json")
        if "exc_info" in kwargs:
            err = kwargs["exc_info"][1]
            self.finish(json.dumps({"error": str(err)}))
        else:
            self.finish(json.dumps({"error": f"HTTP {status_code}"}))

    def _set_bridge_cookie(self) -> None:
        """
        Mint a short-lived signed cookie scoped to '/'.

        This enables root fallback proxy handlers to authorize requests when
        path-scoped Hub auth cookies are not attached to root-relative calls.
        """
        session_id = self.get_cookie("jupyterhub-session-id", default="") or ""
        payload = json.dumps(
            {
                "base_url": self.settings.get("base_url", "/"),
                "sid": session_id,
                "exp": int(time.time()) + BRIDGE_COOKIE_TTL_SECONDS,
            }
        )
        self.set_secure_cookie(
            BRIDGE_COOKIE_NAME,
            payload,
            path="/",
            httponly=True,
            secure=self.request.protocol == "https",
            samesite="Lax",
        )

    @web.authenticated
    async def get(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def post(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def put(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def patch(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def delete(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def options(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    @web.authenticated
    async def head(self, path: str) -> None:
        self._set_bridge_cookie()
        await self._proxy(path)

    def _maybe_rewrite_ui_payload(
        self, *, path: str, content_type: str, body: bytes, base_proxy_url: str
    ) -> bytes:
        """
        Inject a runtime URL rewriter only into the KFP shell HTML document.

        This keeps root-relative KFP UI calls under /<base_url>/kfp-ui/... in
        path-based JupyterHub deployments, where root requests otherwise go to Hub.
        """
        if not body:
            return body

        normalized_path = path.lstrip("/")
        is_shell_document = normalized_path in {"", "index.html"}
        is_html = "text/html" in content_type or normalized_path.endswith(".html")
        if not (is_shell_document and is_html):
            return body

        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError:
            return body

        rewritten = self._inject_runtime_path_rewriter(
            html=html, base_proxy_url=base_proxy_url
        )
        if rewritten == html:
            return body

        self.log.info("KFP UI rewrite applied for %s", path)
        return rewritten.encode("utf-8")

    def _inject_runtime_path_rewriter(self, *, html: str, base_proxy_url: str) -> str:
        if _RUNTIME_REWRITER_SENTINEL in html:
            return html

        safe_base = json.dumps(base_proxy_url.rstrip("/"))
        script = (
            "<script>(function(){"
            f"if(window.{_RUNTIME_REWRITER_SENTINEL})return;"
            f"window.{_RUNTIME_REWRITER_SENTINEL}=true;"
            "var base=" + safe_base + ";"
            "var prefixes=['/ml_metadata.MetadataStoreService/','/system/','/apis/v1beta1/','/apis/v2beta1/','/k8s/'];"
            "function needsRewrite(path){"
            "for(var i=0;i<prefixes.length;i++){if(path.indexOf(prefixes[i])===0){return true;}}"
            "return false;"
            "}"
            "function rewriteUrl(url){"
            "if(typeof url!=='string'){return url;}"
            "if(url.indexOf(base+'/')===0){return url;}"
            "if(needsRewrite(url)){return base+url;}"
            "try{"
            "var parsed=new URL(url,window.location.href);"
            "if(parsed.origin===window.location.origin&&parsed.pathname.indexOf(base+'/')===0){"
            "return parsed.pathname+(parsed.search||'')+(parsed.hash||'');"
            "}"
            "if(parsed.origin===window.location.origin&&needsRewrite(parsed.pathname)){"
            "return base+parsed.pathname+(parsed.search||'')+(parsed.hash||'');"
            "}"
            "}catch(e){}"
            "return url;"
            "}"
            "if(window.fetch){"
            "var _fetch=window.fetch;"
            "window.fetch=function(input,init){"
            "if(typeof input==='string'){return _fetch.call(this,rewriteUrl(input),init);}"
            "if(input&&typeof input.url==='string'){"
            "var newUrl=rewriteUrl(input.url);"
            "if(newUrl!==input.url){input=new Request(newUrl,input);}"
            "}"
            "return _fetch.call(this,input,init);"
            "};"
            "}"
            "if(window.XMLHttpRequest&&window.XMLHttpRequest.prototype){"
            "var _open=window.XMLHttpRequest.prototype.open;"
            "window.XMLHttpRequest.prototype.open=function(method,url){"
            "var args=Array.prototype.slice.call(arguments);"
            "if(args.length>1){args[1]=rewriteUrl(String(url));}"
            "return _open.apply(this,args);"
            "};"
            "}"
            "})();</script>"
        )

        if "<head>" in html:
            return html.replace("<head>", "<head>" + script, 1)
        if "<body>" in html:
            return html.replace("<body>", "<body>" + script, 1)
        return script + html

    async def _proxy(self, path: str) -> None:
        cfg = get_config(self)
        try:
            kfp_endpoint = base_kfp_endpoint(cfg.endpoint).rstrip("/")
        except ValueError as e:
            self.set_status(412)
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({"error": str(e)}))
            return

        kfp_url = f"{kfp_endpoint}/{path.lstrip('/')}"
        if self.request.query:
            kfp_url += f"?{self.request.query}"

        self.log.info(f"KFP Proxy Request: {self.request.method} {path} -> {kfp_url}")

        client = tornado.httpclient.AsyncHTTPClient()

        try:
            hop_by_hop = {
                "host",
                "connection",
                "keep-alive",
                "proxy-authenticate",
                "proxy-authorization",
                "te",
                "trailers",
                "transfer-encoding",
                "upgrade",
            }
            headers: dict[str, str] = {
                h: v for h, v in self.request.headers.items() if h.lower() not in hop_by_hop
            }

            if cfg.token:
                headers["Authorization"] = f"Bearer {cfg.token}"

            request_body = None
            allow_nonstandard_methods = False
            if self.request.method in {"POST", "PUT", "PATCH"}:
                request_body = self.request.body or b""
            elif self.request.method == "DELETE" and self.request.body:
                request_body = self.request.body
                allow_nonstandard_methods = True

            response = await client.fetch(
                kfp_url,
                method=self.request.method,
                headers=headers,
                body=request_body,
                raise_error=False,
                follow_redirects=False,
                decompress_response=True,
                allow_nonstandard_methods=allow_nonstandard_methods,
                connect_timeout=15.0,
                request_timeout=60.0,
            )

            self.log.info(f"KFP Proxy Response: {response.code} for {path}")
            self.set_status(response.code)

            base_proxy_url = url_path_join(self.settings.get("base_url", "/"), "kfp-ui")
            response_content_type = response.headers.get("Content-Type", "")

            for h, v in response.headers.items():
                l_h = h.lower()
                if l_h in {
                    "content-length",
                    "content-encoding",
                    "transfer-encoding",
                    "connection",
                    "set-cookie",
                    "server",
                }:
                    continue

                if l_h == "location":
                    orig_loc = v
                    if orig_loc.startswith(kfp_endpoint):
                        new_loc = orig_loc.replace(kfp_endpoint, base_proxy_url.rstrip("/"), 1)
                    elif orig_loc.startswith("/"):
                        new_loc = url_path_join(base_proxy_url, orig_loc)
                    else:
                        new_loc = orig_loc
                    self.set_header("Location", new_loc)
                    continue

                self.set_header(h, v)

            self.set_header("X-Frame-Options", "SAMEORIGIN")
            self.set_header("Content-Security-Policy", "frame-ancestors 'self'")
            self.set_header("Cache-Control", "no-store, max-age=0")
            self.set_header("Pragma", "no-cache")
            self.set_header("Expires", "0")

            if path.endswith(".js"):
                self.set_header("Content-Type", "application/javascript")
            elif path.endswith(".css"):
                self.set_header("Content-Type", "text/css")

            if response.code != 304:
                rewritten_body = self._maybe_rewrite_ui_payload(
                    path=path,
                    content_type=response_content_type.lower(),
                    body=response.body,
                    base_proxy_url=base_proxy_url,
                )
                if rewritten_body is not response.body:
                    self.set_header("X-Kfp-Ui-Rewrite", "1")
                self.write(rewritten_body)

        except tornado.httpclient.HTTPClientError as e:
            self.log.error(f"UI Proxy HTTPClientError at {path}: {e}", exc_info=True)
            self.set_status(502)
            self.set_header("Content-Type", "application/json")
            self.write(
                json.dumps(
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "kfp_url": kfp_url,
                    }
                )
            )
        except Exception as e:
            self.log.error(f"UI Proxy Exception at {path}: {e}", exc_info=True)
            self.set_status(500)
            self.set_header("Content-Type", "application/json")
            self.write(
                json.dumps(
                    {
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "kfp_url": kfp_url,
                    }
                )
            )


class KfpRootFallbackProxyHandler(KfpUIProxyHandler):
    """
    Root fallback proxy for KFP UI absolute paths (e.g. /ml_metadata...).

    This is a safety net for environments where runtime URL rewrite may be
    bypassed by some clients. Authorization is enforced by either:
    - normal authenticated user session, or
    - a short-lived signed bridge cookie minted by KfpUIProxyHandler.
    """

    def initialize(self, *, base_url: str) -> None:  # type: ignore[override]
        self._base_url = base_url

    def check_xsrf_cookie(self) -> None:
        return

    def _bridge_cookie_ok(self) -> bool:
        raw = self.get_secure_cookie(BRIDGE_COOKIE_NAME, max_age_days=1)
        if not raw:
            return False

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False

        if payload.get("base_url") != self._base_url:
            return False

        expires_at = payload.get("exp")
        if not isinstance(expires_at, int) or expires_at < int(time.time()):
            return False

        expected_session_id = payload.get("sid", "")
        current_session_id = self.get_cookie("jupyterhub-session-id", default="") or ""
        if (
            isinstance(expected_session_id, str)
            and expected_session_id
            and current_session_id
            and expected_session_id != current_session_id
        ):
            return False

        return True

    async def _proxy_if_authorized(self) -> None:
        if self.current_user is None and not self._bridge_cookie_ok():
            self.set_status(403)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps({"error": "Forbidden"}))
            return

        path = self.request.path.lstrip("/")
        await self._proxy(path)

    async def get(self, *args) -> None:
        await self._proxy_if_authorized()

    async def post(self, *args) -> None:
        await self._proxy_if_authorized()

    async def put(self, *args) -> None:
        await self._proxy_if_authorized()

    async def patch(self, *args) -> None:
        await self._proxy_if_authorized()

    async def delete(self, *args) -> None:
        await self._proxy_if_authorized()

    async def head(self, *args) -> None:
        await self._proxy_if_authorized()

    async def options(self, *args) -> None:
        await self._proxy_if_authorized()
