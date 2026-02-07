"""Configuration management for Claw Face."""

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Tuple

# Default config location
CONFIG_DIR = Path.home() / ".config" / "claw-face"
CONFIG_FILE = CONFIG_DIR / "config.json"

log = logging.getLogger(__name__)


@dataclass
class Colors:
    """Color configuration (RGB tuples) - LED dot-matrix style."""
    background: Tuple[int, int, int] = (0, 0, 0)
    eye_white: Tuple[int, int, int] = (230, 235, 240)
    mouth: Tuple[int, int, int] = (220, 225, 230)
    highlight: Tuple[int, int, int] = (255, 255, 255)

    @staticmethod
    def _clamp_rgb(v: object, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        if not isinstance(v, tuple) or len(v) != 3:
            return fallback
        out = []
        for c in v:
            try:
                n = int(c)
            except Exception:
                return fallback
            out.append(max(0, min(255, n)))
        return (out[0], out[1], out[2])

    def validate(self) -> None:
        self.background = self._clamp_rgb(self.background, (0, 0, 0))
        self.eye_white = self._clamp_rgb(self.eye_white, (230, 235, 240))
        self.mouth = self._clamp_rgb(self.mouth, (220, 225, 230))
        self.highlight = self._clamp_rgb(self.highlight, (255, 255, 255))


@dataclass
class Behavior:
    """Behavior timing configuration."""
    blink_interval_min: float = 3.0
    blink_interval_max: float = 6.0
    look_interval_min: float = 2.0
    look_interval_max: float = 5.0
    expression_interval_min: float = 8.0
    expression_interval_max: float = 20.0

    @staticmethod
    def _clamp_nonneg_float(v: object, fallback: float) -> float:
        try:
            n = float(v)  # type: ignore[arg-type]
        except Exception:
            return fallback
        if not (n == n):  # NaN
            return fallback
        return max(0.0, n)

    def validate(self) -> None:
        self.blink_interval_min = self._clamp_nonneg_float(self.blink_interval_min, 3.0)
        self.blink_interval_max = self._clamp_nonneg_float(self.blink_interval_max, 6.0)
        if self.blink_interval_max < self.blink_interval_min:
            self.blink_interval_min, self.blink_interval_max = (
                self.blink_interval_max,
                self.blink_interval_min,
            )

        self.look_interval_min = self._clamp_nonneg_float(self.look_interval_min, 2.0)
        self.look_interval_max = self._clamp_nonneg_float(self.look_interval_max, 5.0)
        if self.look_interval_max < self.look_interval_min:
            self.look_interval_min, self.look_interval_max = (
                self.look_interval_max,
                self.look_interval_min,
            )

        self.expression_interval_min = self._clamp_nonneg_float(self.expression_interval_min, 8.0)
        self.expression_interval_max = self._clamp_nonneg_float(self.expression_interval_max, 20.0)
        if self.expression_interval_max < self.expression_interval_min:
            self.expression_interval_min, self.expression_interval_max = (
                self.expression_interval_max,
                self.expression_interval_min,
            )


@dataclass
class Display:
    """Display / server configuration."""
    host: str = "127.0.0.1"
    port: int = 8420
    fullscreen: bool = True
    fps: int = 30
    window_width: int = 1280
    window_height: int = 720
    # Dot-matrix tuning (larger spacing/radius = fewer dots for same face size)
    dot_spacing: float = 17.0
    dot_radius: float = 6.5

    def validate(self) -> None:
        # Host: leave as-is (string); server binding will handle errors.

        # Port: allow 0 for ephemeral.
        try:
            p = int(self.port)
        except Exception:
            p = 8420
        if p < 0 or p > 65535:
            p = 8420
        self.port = p

        # FPS: clamp to a sensible range.
        try:
            fps = int(self.fps)
        except Exception:
            fps = 30
        self.fps = max(1, min(240, fps))

        # Window sizes.
        try:
            w = int(self.window_width)
        except Exception:
            w = 1280
        try:
            h = int(self.window_height)
        except Exception:
            h = 720
        self.window_width = max(1, w)
        self.window_height = max(1, h)

        # Dot-matrix tuning.
        try:
            ds = float(self.dot_spacing)
        except Exception:
            ds = 17.0
        if not (ds == ds):
            ds = 17.0
        self.dot_spacing = ds if ds >= 2.0 else 17.0

        try:
            dr = float(self.dot_radius)
        except Exception:
            dr = 6.5
        if not (dr == dr):
            dr = 6.5
        self.dot_radius = dr if dr >= 0.5 else 6.5


def _safe_init(cls, data: dict):
    """Instantiate a dataclass, ignoring unknown keys."""
    valid = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class Config:
    """Main configuration container."""
    colors: Colors = field(default_factory=Colors)
    behavior: Behavior = field(default_factory=Behavior)
    display: Display = field(default_factory=Display)

    def validate(self) -> None:
        self.colors.validate()
        self.behavior.validate()
        self.display.validate()

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Save configuration to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        self.validate()
        data = {
            "colors": {k: list(v) if isinstance(v, tuple) else v
                      for k, v in asdict(self.colors).items()},
            "behavior": asdict(self.behavior),
            "display": asdict(self.display),
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config":
        """Load configuration from JSON file, or return defaults."""
        if not path.exists():
            cfg = cls()
            cfg.validate()
            return cfg

        try:
            with open(path) as f:
                data = json.load(f)

            colors = _safe_init(Colors, {
                k: tuple(v) if isinstance(v, list) else v
                for k, v in data.get("colors", {}).items()
            })
            behavior = _safe_init(Behavior, data.get("behavior", {}))
            display = _safe_init(Display, data.get("display", {}))

            cfg = cls(colors=colors, behavior=behavior, display=display)
            cfg.validate()
            return cfg
        except Exception as e:
            log.warning("Could not load config (%s): %s", str(path), e)
            cfg = cls()
            cfg.validate()
            return cfg


def get_config() -> Config:
    """Get the current configuration."""
    return Config.load()
