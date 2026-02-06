#!/usr/bin/env python3
"""
Write Claw Face control files.

This is designed to be used from OpenClaw skills, where shell quoting/sanitization
can get tricky. We validate the expression and write JSON safely.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "claw-face"
COMMAND_FILE = CONFIG_DIR / "command.json"
STATUS_FILE = CONFIG_DIR / "status.txt"

VALID_EXPRESSIONS = {
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprised",
    "sleepy",
    "wink",
    "love",
    "talking",
}


def _parse_bool(s: str) -> bool:
    v = s.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean: {s!r} (use true/false)")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    except OSError:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Control the Claw Face kiosk display.")
    ap.add_argument("--expression", type=str, default=None, help="Expression name")
    ap.add_argument(
        "--auto-cycle",
        type=_parse_bool,
        default=None,
        help="Enable/disable auto-cycling (true/false)",
    )
    ap.add_argument("--status", type=str, default=None, help="Status line text")
    ap.add_argument("--clear-status", action="store_true", help="Clear status.txt")
    ap.add_argument("--clear-command", action="store_true", help="Clear command.json")

    args = ap.parse_args()

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if args.clear_status:
        try:
            STATUS_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    if args.status is not None:
        # Keep it single-line; the UI expects a short string.
        text = " ".join(args.status.splitlines()).strip()
        try:
            STATUS_FILE.write_text(text, encoding="utf-8")
        except OSError:
            pass

    if args.clear_command:
        try:
            COMMAND_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    if args.expression is None and args.auto_cycle is None:
        # Nothing else to do.
        return 0

    if args.expression is not None and args.expression not in VALID_EXPRESSIONS:
        valid = ", ".join(sorted(VALID_EXPRESSIONS))
        raise SystemExit(f"Invalid expression: {args.expression!r}. Valid: {valid}")

    cmd = _load_json(COMMAND_FILE)
    if args.expression is not None:
        cmd["expression"] = args.expression
    if args.auto_cycle is not None:
        cmd["auto_cycle"] = bool(args.auto_cycle)

    try:
        COMMAND_FILE.write_text(json.dumps(cmd, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

