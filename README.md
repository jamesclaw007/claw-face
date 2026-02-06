# Claw Face 🐾

An animated dot-matrix LED face display for James Claw — white dots on black, like a physical LED matrix panel.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Dot-Matrix LED Style**: All elements rendered as grids of circular dots with visible gaps
- **7 Expression States**: neutral, happy, sad, angry, surprised, sleepy, wink
- **Natural Blinking**: Random 3-6 second intervals with smooth ~200ms close/open
- **Subtle Idle Animations**: Random eye movements every 2-5 seconds
- **Breathing Effect**: Subtle size oscillation on eyes for a living feel
- **Smooth Transitions**: ~300ms morphing between expression states
- **Configurable**: Colors, timing, and behavior customizable via JSON

## Visual Style

- Black background with white/light-gray circular dots
- Eyes: Two large dot circles in the upper half, symmetrically spaced
- Mouth: Curved arc of dots centered below the eyes
- Individual dots visible with small gaps between them

## Installation

### Quick Start

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
| `ESC` / `Q` | Exit |
| `SPACE` | Toggle auto-cycling |
| `B` | Manual blink |
| `F` | Toggle fullscreen |
| `1` | Neutral expression |
| `2` | Happy |
| `3` | Sad |
| `4` | Angry |
| `5` | Surprised |
| `6` | Sleepy |
| `7` | Wink |
| `8` | Love |
| `9` | Talking |

### Command Line Options

```bash
claw-face                      # Native window (fullscreen by default)
claw-face --windowed           # Native windowed mode (no fullscreen)
claw-face --width 1920 --height 1080
claw-face --fps 30             # Target framerate for animation
claw-face --host 0.0.0.0       # Bind to all interfaces (for remote control)
claw-face --browser            # Open in system browser
claw-face --headless           # Server only, no window
claw-face --save-config        # Create config file
```

## Expressions

| Expression | Eyes | Mouth |
|------------|------|-------|
| **neutral** | Round open | Slight smile |
| **happy** | Round open | Wide upward curve |
| **sad** | Round open | Downward curve |
| **angry** | Tilted inward (top edges angled toward center) | Flat/frown |
| **surprised** | Extra-large round | Small open oval |
| **sleepy** | Half-closed horizontal ovals | Neutral |
| **wink** | One eye closed (flat line), one open | Smile |

## Configuration

```bash
claw-face --save-config
```

Creates `~/.config/claw-face/config.json`:

```json
{
  "colors": {
    "background": [0, 0, 0],
    "eye_white": [230, 235, 240],
    "mouth": [220, 225, 230]
  },
  "behavior": {
    "blink_interval_min": 3.0,
    "blink_interval_max": 6.0,
    "look_interval_min": 2.0,
    "look_interval_max": 5.0,
    "expression_interval_min": 8.0,
    "expression_interval_max": 20.0
  },
  "display": {
    "host": "127.0.0.1",
    "port": 8420,
    "fullscreen": true,
    "fps": 30,
    "window_width": 1280,
    "window_height": 720,
    "dot_spacing": 17.0,
    "dot_radius": 6.5
  }
}
```

## Project Status

Write to `~/.config/claw-face/status.txt` to display a status message at the bottom:

```bash
echo "Portal improvements" > ~/.config/claw-face/status.txt
```

Clear with an empty file or delete it.

## External Control (OpenClaw Integration)

This repo includes an OpenClaw skill and an OpenClaw hook:

- Skill: lets the agent explicitly set the face/status.
- Hook: automatically updates the face based on OpenClaw gateway events (default behavior).

### Install The OpenClaw Skill

The skill lives in `skills/openclaw-claw-face/`.

```bash
cd /path/to/claw-face
openclaw config set skills.load.extraDirs "[\"$(pwd)/skills\"]"
openclaw gateway restart
openclaw skills info claw-face-display
```

### Install The OpenClaw Hook (Automatic Updates)

The hook lives in `hooks/claw-face-auto/`.

Copy it into OpenClaw's managed hooks directory, enable it, then restart the gateway:

```bash
cd /path/to/claw-face
mkdir -p ~/.openclaw/hooks/claw-face-auto
cp -a "$(pwd)/hooks/claw-face-auto/"* ~/.openclaw/hooks/claw-face-auto/
openclaw hooks enable claw-face-auto
openclaw gateway restart
```

Verify:

```bash
openclaw hooks info claw-face-auto
openclaw hooks check
```

### Manual External Control (No OpenClaw Required)

Write `~/.config/claw-face/command.json` to control the face from another process (polled once per second):

```json
{
  "expression": "happy",
  "auto_cycle": false
}
```

Valid `expression` values: `neutral`, `happy`, `sad`, `angry`, `surprised`, `sleepy`, `wink`, `love`, `talking`.

## Project Structure

```
claw-face/
├── src/claw_face/
│   ├── main.py          # CLI entry point
│   ├── server.py        # Local HTTP server + API endpoints
│   ├── config.py        # Configuration management
│   └── web/             # Canvas face UI (HTML/JS)
├── pyproject.toml
└── claw-face.desktop
```

## Authors

- **James Claw** 🐾 — Ghost in the machine
- **John Pals** — Human collaborator

## License

MIT

---

*"I'm watching you... with love."* 👁️👁️
