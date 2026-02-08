from __future__ import annotations

import json
import threading
import urllib.request

from claw_face.expressions import ALL_VALID, CANONICAL, COMPAT_MAP, SPECIAL, WEIGHTS


def test_weights_keys_match_canonical() -> None:
    assert set(WEIGHTS.keys()) == set(CANONICAL)


def test_compat_values_are_canonical() -> None:
    canonical_set = set(CANONICAL)
    for alias, target in COMPAT_MAP.items():
        assert target in canonical_set, f"compat alias {alias!r} -> {target!r} is not canonical"


def test_all_valid_is_correct_union() -> None:
    expected = set(CANONICAL) | set(COMPAT_MAP) | set(SPECIAL)
    assert ALL_VALID == expected


def test_expressions_endpoint() -> None:
    from claw_face.config import Config
    from claw_face.server import _start_server

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
        url = f"http://{host}:{port}/api/expressions"
        with urllib.request.urlopen(url, timeout=2) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))

        assert isinstance(data["canonical"], list)
        assert len(data["canonical"]) == len(CANONICAL)
        assert isinstance(data["compat"], dict)
        assert isinstance(data["special"], list)
        assert isinstance(data["weights"], dict)
        assert set(data["weights"].keys()) == set(data["canonical"])
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=2)
