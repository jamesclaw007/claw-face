"""Canonical expression definitions for Claw Face."""

from __future__ import annotations

# The 16 canonical expression names (matching PRESETS in index.html)
CANONICAL: list[str] = [
    "normal",
    "happy",
    "sad",
    "angry",
    "surprised",
    "suspicious",
    "cute",
    "tired",
    "wonder",
    "upset",
    "confused",
    "scared",
    "sleepy",
    "glee",
    "skeptic",
    "thinking",
]

# Backward-compat aliases → canonical name
COMPAT_MAP: dict[str, str] = {
    "neutral": "normal",
    "love": "cute",
    "focused": "suspicious",
    "excited": "glee",
    "glitch": "scared",
    "smug": "skeptic",
    "sleep": "sleepy",
}

# Special names handled by custom logic (not presets)
SPECIAL: list[str] = ["wink", "talking", "typing"]

# Weighted random distribution for auto-cycling
WEIGHTS: dict[str, int] = {
    "normal": 25,
    "happy": 35,
    "sad": 5,
    "angry": 3,
    "surprised": 8,
    "suspicious": 6,
    "cute": 6,
    "tired": 4,
    "wonder": 5,
    "upset": 3,
    "confused": 3,
    "scared": 1,
    "sleepy": 12,
    "glee": 4,
    "skeptic": 6,
    "thinking": 8,
}

# Union of all valid expression names
ALL_VALID: set[str] = set(CANONICAL) | set(COMPAT_MAP) | set(SPECIAL)
