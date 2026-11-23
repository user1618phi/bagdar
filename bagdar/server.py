"""Web server: a small JSON API and the static web app. Standard library only.

    GET  /api/pack       destinations and skill names
    GET  /api/model      parameters, the solved MDP and its convergence
    GET  /api/evidence   results of the experiments: simulated learners and real answer logs
    POST /api/state      {targets, history, pin?, lesson?, inspect?} -> full session state
    POST /api/compare    {targets, history} -> A* vs UCS vs greedy vs BFS on the current route
    GET  /health         liveness probe

The server keeps no session state: the browser owns the history and sends it with each request.
"""

from __future__ import annotations

import json
import mimetypes
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .content import load_pack
from .tutor import Tutor

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
RESULTS_FILE = ROOT / "docs" / "results.json"
REAL_RESULTS_FILE = ROOT / "docs" / "results_real.json"
MAX_BODY_BYTES = 1_000_000

# Sent with every response. The page needs no third-party origin at all: scripts, styles and
# fonts are served from here (fonts inside kit.css are data: URIs), and the API is same-origin.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; font-src 'self' data:; "
                               "style-src 'self'; script-src 'self'; connect-src 'self'; "
                               "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
}


def build_tutor() -> Tutor:
    return Tutor(load_pack())


class Handler(BaseHTTPRequestHandler):
    tutor: Tutor
    server_version = "Bagdar/1.0"

    timeout = 15  # seconds: a stalled client cannot hold a worker thread forever

    def log_message(self, format: str, *args) -> None:  # keep the console quiet during a demo
        if getattr(self.server, "verbose", False):
            super().log_message(format, *args)

    def end_headers(self) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    # ---------------------------------------------------------------- routing

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._json({"status": "ok"})
        elif path == "/api/pack":
            pack = self.tutor.pack
            self._json({
                "id": pack.id, "title": pack.title, "source": pack.source, "groups": list(pack.groups),
                "destinations": list(pack.destinations),
                "skills": [{"id": s.id, "name": s.name, "short": s.short, "group": s.group} for s in pack.skills.values()],
                "items": len(pack.items),
            })
        elif path == "/api/model":
            self._json(self.tutor.describe_model())
        elif path == "/api/evidence":
            if RESULTS_FILE.exists():
                evidence = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
                if REAL_RESULTS_FILE.exists():
                    evidence["real"] = json.loads(REAL_RESULTS_FILE.read_text(encoding="utf-8"))
                self._json(evidence)
            else:
                self._json({"error": "No results yet. Run: python -m bagdar experiments"}, HTTPStatus.NOT_FOUND)
        elif path.startswith("/api/"):
            self._json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        else:
            self._static(path)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path not in ("/api/state", "/api/compare"):
            self._json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
            return
        try:
            body = self._read_json()
        except ValueError as error:
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        targets = body.get("targets") if isinstance(body.get("targets"), list) else []
        history = body.get("history") if isinstance(body.get("history"), list) else []
        try:
            if path == "/api/compare":
                self._json({"results": self.tutor.compare_search(targets, history)})
            else:
                pin = body.get("pin") if isinstance(body.get("pin"), str) else None
                inspect = body.get("inspect") if isinstance(body.get("inspect"), str) else None
                self._json(self.tutor.replay(targets, history, pin, bool(body.get("lesson")), inspect))
        except Exception as error:  # never let one bad request take the demo down
            print(f"error while handling {path}: {error!r}", file=sys.stderr)
            self._json({"error": "The engine could not process this request."}, HTTPStatus.INTERNAL_SERVER_ERROR)

    # ---------------------------------------------------------------- helpers

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length") from None
        if length > MAX_BODY_BYTES:
            raise ValueError("Request body is too large")
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Request body must be valid JSON") from None
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")
        return body

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=_encode).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (WEB_DIR / relative).resolve()
        if WEB_DIR.resolve() not in target.parents or not target.is_file():
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def _encode(value: object) -> object:
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if value == float("inf"):
        return None
    raise TypeError(f"cannot encode {type(value).__name__}")


def make_server(host: str = "127.0.0.1", port: int = 8000, verbose: bool = False) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"tutor": build_tutor()})
    server = ThreadingHTTPServer((host, port), handler)
    server.verbose = verbose  # type: ignore[attr-defined]
    return server


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True, verbose: bool = False) -> None:
    """Run until interrupted. Binds to this machine only unless a host is given (see Dockerfile)."""
    try:
        server = make_server(host, port, verbose)
    except OSError as error:
        raise SystemExit(f"Cannot start on port {port} ({error.strerror}). Try: python -m bagdar serve --port {port + 1}")
    url = f"http://{host}:{server.server_address[1]}"
    print(f"Bagdar is running at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
