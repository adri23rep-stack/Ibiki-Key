from __future__ import annotations

import hmac
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

log = logging.getLogger(__name__)


class LocalApiServer:
    def __init__(
        self,
        status: Callable[[], dict[str, Any]],
        activate_profile: Callable[[str, str], None],
        run_macro: Callable[[str, str | None], None],
        get_variables: Callable[[], dict[str, Any]],
        set_variable: Callable[[str, Any], None],
    ):
        self.status = status
        self.activate_profile = activate_profile
        self.run_macro = run_macro
        self.get_variables = get_variables
        self.set_variable = set_variable
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.token = ""

    def start(self, port: int, token: str) -> None:
        self.stop()
        self.token = token
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "IbikiKey/0.4"

            def log_message(self, fmt: str, *args: object) -> None:
                log.info("API: " + fmt, *args)

            def _authorized(self) -> bool:
                if not owner.token:
                    return True
                header = self.headers.get("Authorization", "")
                expected = f"Bearer {owner.token}"
                return hmac.compare_digest(header, expected)

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self._cors_headers()
                self.end_headers()
                self.wfile.write(data)

            def _cors_headers(self) -> None:
                origin = self.headers.get("Origin", "")
                parsed = urlparse(origin)
                if parsed.scheme in {"http", "https"} and parsed.hostname in {
                    "127.0.0.1",
                    "localhost",
                    "::1",
                }:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

            def _body(self) -> dict[str, Any]:
                length = min(int(self.headers.get("Content-Length", "0")), 64_000)
                if not length:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))

            def do_GET(self) -> None:  # noqa: N802
                if not self._authorized():
                    self._json(401, {"error": "unauthorized"})
                    return
                path = urlparse(self.path).path
                if path in {"/", "/health", "/v1/status"}:
                    self._json(200, owner.status())
                elif path == "/v1/variables":
                    self._json(200, {"variables": owner.get_variables()})
                else:
                    self._json(404, {"error": "not_found"})

            def do_OPTIONS(self) -> None:  # noqa: N802
                origin = self.headers.get("Origin", "")
                parsed = urlparse(origin)
                if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                    self._json(403, {"error": "origin_not_allowed"})
                    return
                self.send_response(204)
                self._cors_headers()
                self.end_headers()

            def do_POST(self) -> None:  # noqa: N802
                if not self._authorized():
                    self._json(401, {"error": "unauthorized"})
                    return
                try:
                    path = urlparse(self.path).path
                    body = self._body()
                    if path.startswith("/v1/profiles/") and path.endswith("/activate"):
                        profile_id = path.split("/")[3]
                        owner.activate_profile(profile_id, "API local")
                        self._json(200, {"ok": True})
                    elif path.startswith("/v1/macros/") and path.endswith("/run"):
                        macro_id = path.split("/")[3]
                        owner.run_macro(macro_id, None)
                        self._json(202, {"ok": True})
                    elif path.startswith("/v1/variables/"):
                        name = path.split("/")[3]
                        owner.set_variable(name, body.get("value"))
                        self._json(200, {"ok": True})
                    else:
                        self._json(404, {"error": "not_found"})
                except Exception as exc:
                    self._json(400, {"error": str(exc)})

        self.server = ThreadingHTTPServer(("127.0.0.1", int(port)), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, name="IbikiLocalAPI", daemon=True)
        self.thread.start()
        log.info("API local activa en 127.0.0.1:%s", port)

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.server = None
        self.thread = None
