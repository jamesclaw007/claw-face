import ipaddress
import json
import logging
import threading
import webbrowser
from functools import partial
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from .config import CONFIG_DIR, Config

STATUS_FILE = CONFIG_DIR / "status.txt"
COMMAND_FILE = CONFIG_DIR / "command.json"
WEB_DIR = Path(__file__).parent / "web"

log = logging.getLogger(__name__)


def _is_loopback_address(addr: str) -> bool:
    try:
        return ipaddress.ip_address(addr).is_loopback
    except ValueError:
        return False


class ClawFaceHandler(SimpleHTTPRequestHandler):
    """Request handler with API endpoints and static file serving."""

    webview_window = None  # Set by _run_webview when in webview mode

    def __init__(self, *args, config: Config, **kwargs):
        self.config = config
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _require_loopback(self) -> bool:
        ip = ""
        try:
            ip = str(self.client_address[0])
        except Exception:
            ip = ""
        if _is_loopback_address(ip):
            return True
        self.send_response(HTTPStatus.FORBIDDEN)
        body = json.dumps({"ok": False, "error": "forbidden"}).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        if self.path == '/api/status':
            self._handle_status()
        elif self.path == '/api/command':
            self._handle_command()
        elif self.path == '/api/config':
            self._handle_config()
        elif self.path == '/api/fullscreen/toggle':
            self._handle_fullscreen_toggle()
        elif self.path == '/api/quit':
            self._handle_quit()
        else:
            super().do_GET()

    def _handle_quit(self):
        if not self._require_loopback():
            return
        self._json_response({"ok": True})
        w = ClawFaceHandler.webview_window
        if w:
            w.destroy()
        else:
            # headless/browser mode — stop the server
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _handle_status(self):
        text = ""
        try:
            if STATUS_FILE.exists():
                text = STATUS_FILE.read_text().strip()
        except OSError:
            pass
        self._json_response({"text": text})

    def _handle_command(self):
        data = {}
        try:
            if COMMAND_FILE.exists():
                raw = COMMAND_FILE.read_text().strip()
                if raw:
                    data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            data = {}
        # Keep the surface area small: only return known keys.
        out: dict[str, object] = {}
        if isinstance(data, dict):
            if isinstance(data.get("expression"), str):
                out["expression"] = data["expression"]
            if isinstance(data.get("auto_cycle"), bool):
                out["auto_cycle"] = data["auto_cycle"]

            # v2 extensions (all optional)
            intensity = data.get("intensity")
            if isinstance(intensity, (int, float)) and intensity == intensity:
                out["intensity"] = max(0.0, min(1.0, float(intensity)))

            look = data.get("look")
            if isinstance(look, dict):
                x = look.get("x")
                y = look.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and x == x and y == y:
                    out["look"] = {
                        "x": max(-1.0, min(1.0, float(x))),
                        "y": max(-1.0, min(1.0, float(y))),
                    }

            blink_seq = data.get("blink_seq")
            if isinstance(blink_seq, (int, float)) and blink_seq == blink_seq:
                out["blink_seq"] = int(blink_seq)

            seq = data.get("sequence")
            if isinstance(seq, str):
                out["sequence"] = seq
            seq_seq = data.get("sequence_seq")
            if isinstance(seq_seq, (int, float)) and seq_seq == seq_seq:
                out["sequence_seq"] = int(seq_seq)
        self._json_response(out)

    def _handle_config(self):
        from dataclasses import asdict
        data = {
            "behavior": asdict(self.config.behavior),
            "colors": {
                k: list(v) if isinstance(v, tuple) else v
                for k, v in asdict(self.config.colors).items()
            },
            "display": asdict(self.config.display),
        }
        self._json_response(data)

    def _handle_fullscreen_toggle(self):
        if not self._require_loopback():
            return
        w = ClawFaceHandler.webview_window
        ok = False
        if w is not None:
            # Best-effort: API support depends on the pywebview backend.
            toggle = getattr(w, "toggle_fullscreen", None)
            if callable(toggle):
                try:
                    toggle()
                    ok = True
                except Exception:
                    ok = False
        self._json_response({"ok": ok})

    def _json_response(self, data):
        body = json.dumps(data).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress per-request logging for clean terminal
        pass


def _start_server(config, port):
    """Create and return an HTTPServer, or None on failure."""
    handler = partial(ClawFaceHandler, config=config)
    host = getattr(config.display, "host", "127.0.0.1")
    try:
        return HTTPServer((host, port), handler)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            msg = f"port {port} is already in use"
            log.error(msg)
            print(f"Error: {msg}. Try --port <number>.")
            return None
        raise


def run_server(config: Config, port: int = 8420, mode: str = "webview"):
    """Start Claw Face.

    mode: "webview" (native fullscreen window), "browser" (system browser),
          or "headless" (server only).
    """
    config.validate()
    server = _start_server(config, port)
    if server is None:
        return 1

    host = getattr(config.display, "host", "127.0.0.1")
    # If we bind to all interfaces, pick a sensible loopback URL for the local UI.
    url_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    # If port=0 was used (ephemeral), use the actual bound port.
    actual_port = int(server.server_address[1])
    url = f"http://{url_host}:{actual_port}"

    if mode == "webview":
        return _run_webview(server, url, config)
    elif mode == "browser":
        return _run_browser(server, url)
    else:
        return _run_headless(server, url)


def _run_webview(server, url, config: Config):
    """Native fullscreen window via pywebview (GTK+WebKit on Linux)."""
    import webview

    # Run HTTP server in a background daemon thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"Claw Face running at {url}")
    d = config.display
    fullscreen = bool(getattr(d, "fullscreen", True))
    width = int(getattr(d, "window_width", 1280))
    height = int(getattr(d, "window_height", 720))
    window = webview.create_window(
        "Claw Face",
        url,
        fullscreen=fullscreen,
        width=width,
        height=height,
    )
    ClawFaceHandler.webview_window = window
    webview.start()

    # webview.start() blocks until all windows are closed, then returns
    server.shutdown()
    return 0


def _run_browser(server, url):
    """Open in system browser and serve until Ctrl+C."""
    print(f"Claw Face running at {url}")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.5, webbrowser.open, args=[url]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()
    return 0


def _run_headless(server, url):
    """Server only, no window."""
    print(f"Claw Face server running at {url}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()
    return 0
