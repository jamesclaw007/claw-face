#!/usr/bin/env python3
"""
Claw Face - Main entry point

Run with:
  PYTHONPATH=src python3 -m claw_face
Or after install:
  claw-face
"""

import argparse
import logging
import sys

from . import __version__
from .config import CONFIG_FILE, Config


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claw Face - An animated face display",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Controls:
  1-9       Switch expression
  SPACE     Toggle auto-cycling
  F         Toggle fullscreen

Examples:
  claw-face                    # Native fullscreen window (default)
  claw-face --browser          # Open in system browser instead
  claw-face --headless         # Server only, no window
  claw-face --windowed         # Webview in a resizable window
  claw-face --fps 20           # Lower framerate (kiosk power savings)
  claw-face --save-config      # Save default config to edit
""",
    )

    parser.add_argument("--version", "-v", action="version", version=f"Claw Face {__version__}")

    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO",
    )

    parser.add_argument(
        "--host", type=str, default=None, help="HTTP server host/interface (default: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=None, help="HTTP server port (default: 8420)")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--browser", action="store_true", help="Open in system browser instead of native window"
    )
    mode.add_argument(
        "--headless", action="store_true", help="Run server only, no window or browser"
    )

    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Run native windowed mode (disables fullscreen in webview mode)",
    )
    parser.add_argument(
        "--width", type=int, default=None, help="Window width for --windowed (default from config)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Window height for --windowed (default from config)",
    )
    parser.add_argument(
        "--fps", type=int, default=None, help="Target FPS for animation (default from config)"
    )

    parser.add_argument(
        "--config", "-c", type=str, help=f"Path to config file (default: {CONFIG_FILE})"
    )

    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save default configuration to config file and exit",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("claw_face")

    # Handle --save-config
    if args.save_config:
        config = Config()
        config.save()
        print(f"Default configuration saved to: {CONFIG_FILE}")
        print("Edit this file to customize colors, behavior, and display settings.")
        return 0

    # Load config
    if args.config:
        from pathlib import Path

        config = Config.load(Path(args.config))
    else:
        config = Config.load()

    # Apply command line overrides
    if args.host is not None:
        config.display.host = args.host
    if args.port is not None:
        config.display.port = args.port
    if args.windowed:
        config.display.fullscreen = False
    if args.width is not None:
        config.display.window_width = args.width
    if args.height is not None:
        config.display.window_height = args.height
    if args.fps is not None:
        config.display.fps = args.fps
    config.validate()

    # Determine display mode
    if args.browser:
        mode = "browser"
    elif args.headless:
        mode = "headless"
    else:
        mode = "webview"

    # Run the web server
    from .server import run_server

    try:
        return run_server(config, port=config.display.port, mode=mode)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception:
        log.exception("Fatal error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
