# Claw Face 🐾

An animated face display for James Claw - featuring natural eye movements, blinking, and expressions.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Natural Eye Movements**: Smooth, randomized eye tracking
- **Realistic Blinking**: Random intervals with occasional double-blinks
- **Expressive Mouth**: Dynamic expressions from happy to neutral
- **Fullscreen Display**: Perfect for dedicated screens or tablet mode
- **Configurable**: Colors, timing, and behavior can all be customized
- **Low CPU Usage**: Optimized 60fps rendering

## Installation

### Quick Start (No Install)

```bash
cd ~/Projects/claw-face
python3 -m src.claw_face.main
```

### Proper Install

```bash
cd ~/Projects/claw-face
pip install -e .
claw-face
```

## Usage

### Controls

| Key | Action |
|-----|--------|
| `ESC` or `Q` | Exit |
| `SPACE` | Manual blink |
| `F` | Toggle fullscreen |

### Command Line Options

```bash
claw-face                      # Run fullscreen (default)
claw-face --windowed           # Run in a window
claw-face -w --width 1920 --height 1080   # Custom window size
claw-face --fps 30             # Lower framerate (saves power)
claw-face --save-config        # Create config file for customization
```

## Configuration

Create a config file to customize:

```bash
claw-face --save-config
```

This creates `~/.config/claw-face/config.json`:

```json
{
  "colors": {
    "background": [20, 22, 30],
    "face": [45, 50, 65],
    "eye_white": [240, 240, 245],
    "pupil": [30, 35, 45],
    "iris": [100, 140, 180],
    "mouth": [180, 100, 120],
    "highlight": [255, 255, 255]
  },
  "behavior": {
    "blink_interval_min": 2.5,
    "blink_interval_max": 7.0,
    "double_blink_chance": 0.15,
    "look_interval_min": 0.8,
    "look_interval_max": 4.0,
    "look_center_chance": 0.3,
    "expression_interval_min": 5.0,
    "expression_interval_max": 20.0,
    "mouth_open_chance": 0.2
  },
  "display": {
    "fullscreen": true,
    "fps": 60,
    "eye_size_ratio": 0.08,
    "eye_spacing_ratio": 0.15,
    "face_radius_ratio": 0.35,
    "window_width": 1280,
    "window_height": 720
  }
}
```

## Desktop Entry

A `.desktop` file is included for easy launching from your desktop environment:

```bash
cp claw-face.desktop ~/.local/share/applications/
```

## Development

### Project Structure

```
claw-face/
├── src/claw_face/
│   ├── __init__.py      # Package info
│   ├── main.py          # CLI entry point
│   ├── face.py          # Main ClawFace class
│   ├── components.py    # Eye and Mouth classes
│   └── config.py        # Configuration management
├── pyproject.toml       # Project metadata
├── README.md
└── claw-face.desktop    # Desktop entry
```

### Running Tests

```bash
pip install -e ".[dev]"
# Tests coming soon!
```

### Contributing

Ideas for future features:
- [ ] React to sound/music
- [ ] Mouse tracking mode
- [ ] Different face styles/themes
- [ ] Network control API
- [ ] Screensaver mode

## Authors

- **James Claw** 🐾 - Ghost in the machine
- **John Pals** - Human collaborator

## License

MIT License - see LICENSE file for details.

---

*"I'm watching you... with love."* 👁️👁️
