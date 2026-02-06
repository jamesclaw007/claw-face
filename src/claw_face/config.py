"""Configuration management for Claw Face."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Tuple

# Default config location
CONFIG_DIR = Path.home() / ".config" / "claw-face"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Colors:
    """Color configuration (RGB tuples)."""
    background: Tuple[int, int, int] = (0, 0, 0)  # Pure black for LED look
    face: Tuple[int, int, int] = (0, 0, 0)  # No face circle, just dots
    eye_white: Tuple[int, int, int] = (255, 255, 255)  # Bright white dots
    pupil: Tuple[int, int, int] = (30, 35, 45)
    iris: Tuple[int, int, int] = (100, 140, 180)
    mouth: Tuple[int, int, int] = (255, 255, 255)  # White mouth line
    highlight: Tuple[int, int, int] = (255, 255, 255)


@dataclass
class Behavior:
    """Behavior timing configuration."""
    blink_interval_min: float = 2.5
    blink_interval_max: float = 7.0
    double_blink_chance: float = 0.15
    
    look_interval_min: float = 0.8
    look_interval_max: float = 4.0
    look_center_chance: float = 0.3
    
    expression_interval_min: float = 5.0
    expression_interval_max: float = 20.0
    mouth_open_chance: float = 0.2


@dataclass
class Display:
    """Display configuration."""
    fullscreen: bool = True
    fps: int = 60
    eye_size_ratio: float = 0.08  # Relative to screen size
    eye_spacing_ratio: float = 0.15
    face_radius_ratio: float = 0.35
    window_width: int = 1280  # Used when not fullscreen
    window_height: int = 720


@dataclass
class Config:
    """Main configuration container."""
    colors: Colors = field(default_factory=Colors)
    behavior: Behavior = field(default_factory=Behavior)
    display: Display = field(default_factory=Display)
    
    def save(self, path: Path = CONFIG_FILE) -> None:
        """Save configuration to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict with tuple support
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
            
            colors = Colors(**{k: tuple(v) if isinstance(v, list) else v 
                              for k, v in data.get("colors", {}).items()})
            behavior = Behavior(**data.get("behavior", {}))
            display = Display(**data.get("display", {}))
            
            return cls(colors=colors, behavior=behavior, display=display)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return cls()


def get_config() -> Config:
    """Get the current configuration."""
    return Config.load()
