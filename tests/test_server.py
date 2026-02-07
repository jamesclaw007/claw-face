from __future__ import annotations

import json
import threading
import urllib.request

from claw_face.config import Config
from claw_face.server import _is_loopback_address, _start_server


def test_is_loopback_address() -> None:
    assert _is_loopback_address("127.0.0.1") is True
    assert _is_loopback_address("::1") is True
    assert _is_loopback_address("192.168.0.1") is False
    assert _is_loopback_address("not-an-ip") is False


def test_server_status_endpoint_works() -> None:
    cfg = Config()
    cfg.display.host = "127.0.0.1"
    cfg.display.port = 0
    cfg.validate()

    server = _start_server(cfg, 0)
    assert server is not None
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        host, port = server.server_address[0], int(server.server_address[1])
        url = f"http://{host}:{port}/api/status"
        with urllib.request.urlopen(url, timeout=2) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "text" in data
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=2)

