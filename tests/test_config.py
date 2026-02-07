from __future__ import annotations

import json
from pathlib import Path

from claw_face.config import Config


def test_unknown_keys_ignored(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps(
            {
                "colors": {"background": [1, 2, 3], "unknown": 123},
                "behavior": {"blink_interval_min": 1, "nope": True},
                "display": {"fps": 60, "wat": "ok"},
                "top_level_unknown": 1,
            }
        )
    )
    cfg = Config.load(p)
    assert cfg.colors.background == (1, 2, 3)
    assert cfg.display.fps == 60


def test_validation_clamps_and_normalizes(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps(
            {
                "colors": {"background": [-10, 260, 5]},
                "behavior": {"blink_interval_min": 10, "blink_interval_max": 3},
                "display": {
                    "fps": 9999,
                    "port": 99999,
                    "dot_spacing": 0,
                    "dot_radius": 0.1,
                    "window_width": 0,
                    "window_height": -1,
                },
            }
        )
    )
    cfg = Config.load(p)
    assert cfg.colors.background == (0, 255, 5)
    assert cfg.behavior.blink_interval_min <= cfg.behavior.blink_interval_max
    assert 1 <= cfg.display.fps <= 240
    assert 0 <= cfg.display.port <= 65535
    assert cfg.display.dot_spacing >= 2
    assert cfg.display.dot_radius >= 0.5
    assert cfg.display.window_width >= 1
    assert cfg.display.window_height >= 1

