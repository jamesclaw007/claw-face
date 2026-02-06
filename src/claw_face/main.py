#!/usr/bin/env python3
"""
Claw Face - Main entry point

Run with: python -m claw_face
Or after install: claw-face
"""

import argparse
import sys

from . import __version__
from .config import Config, CONFIG_FILE
from .face import ClawFace


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claw Face - An animated face display 🐾",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Controls:
  ESC, Q    Exit
  SPACE     Manual blink
  F         Toggle fullscreen

Examples:
  claw-face                    # Run fullscreen
  claw-face --windowed         # Run in a window
  claw-face --save-config      # Save default config to edit
"""
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"Claw Face {__version__}"
    )
    
    parser.add_argument(
        "--windowed", "-w",
        action="store_true",
        help="Run in windowed mode instead of fullscreen"
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Window width in windowed mode (default: 1280)"
    )
    
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Window height in windowed mode (default: 720)"
    )
    
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Target frames per second (default: 60)"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help=f"Path to config file (default: {CONFIG_FILE})"
    )
    
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save default configuration to config file and exit"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
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
    if args.windowed:
        config.display.fullscreen = False
    if args.width:
        config.display.window_width = args.width
    if args.height:
        config.display.window_height = args.height
    if args.fps:
        config.display.fps = args.fps
    
    # Run the face
    try:
        face = ClawFace(config)
        face.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
