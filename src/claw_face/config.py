"""Configuration management for Claw Face."""

import json
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from typing import Tuple

# Default config location
CONFIG_DIR = Path.home() / ".config" / "claw-face"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Colors:
    """Color configuration (RGB tuples) - LED dot-matrix style."""
    background: Tuple[int, int, int] = (0, 0, 0)
    eye_white: Tuple[int, int, int] = (230, 235, 240)
    mouth: Tuple[int, int, int] = (220, 225, 230)
    highlight: Tuple[int, int, int] = (255, 255, 255)


@dataclass
class Behavior:
    """Behavior timing configuration."""
    blink_interval_min: float = 3.0
    blink_interval_max: float = 6.0
    look_interval_min: float = 2.0
    look_interval_max: float = 5.0
    expression_interval_min: float = 8.0
    expression_interval_max: float = 20.0


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

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Save configuration to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)

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
            return cls()

        try:
            with open(path) as f:
                data = json.load(f)

            colors = _safe_init(Colors, {
                k: tuple(v) if isinstance(v, list) else v
                for k, v in data.get("colors", {}).items()
            })
            behavior = _safe_init(Behavior, data.get("behavior", {}))
            display = _safe_init(Display, data.get("display", {}))

            return cls(colors=colors, behavior=behavior, display=display)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return cls()


def get_config() -> Config:
    """Get the current configuration."""
    return Config.load()
