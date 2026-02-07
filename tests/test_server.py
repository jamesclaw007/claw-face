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


def test_server_command_endpoint_v2_filters_and_clamps(tmp_path) -> None:
    # Patch the module-level command path to avoid touching the user's config dir.
    import claw_face.server as server_mod

    orig_cmd = server_mod.COMMAND_FILE
    try:
        server_mod.COMMAND_FILE = tmp_path / "command.json"
        server_mod.COMMAND_FILE.write_text(
            json.dumps(
                {
                    "expression": "thinking",
                    "auto_cycle": False,
                    "intensity": 2.5,  # clamp -> 1.0
                    "look": {"x": -2, "y": 0.25},  # clamp x -> -1.0
                    "blink_seq": 123.9,  # int -> 123
                    "sequence": "boot",
                    "sequence_seq": 7,
                    "unknown": True,
                    "look_bad": {"x": "no", "y": []},
                }
            )
        )

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
            url = f"http://{host}:{port}/api/command"
            with urllib.request.urlopen(url, timeout=2) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))

            assert data["expression"] == "thinking"
            assert data["auto_cycle"] is False
            assert data["intensity"] == 1.0
            assert data["look"] == {"x": -1.0, "y": 0.25}
            assert data["blink_seq"] == 123
            assert data["sequence"] == "boot"
            assert data["sequence_seq"] == 7
            assert "unknown" not in data
        finally:
            server.shutdown()
            server.server_close()
            t.join(timeout=2)
    finally:
        server_mod.COMMAND_FILE = orig_cmd
