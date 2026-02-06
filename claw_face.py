#!/usr/bin/env python3
"""
Legacy entry point - redirects to the new modular structure.
Use: python3 -m src.claw_face.main
Or:  ./launch.sh
"""

if __name__ == "__main__":
    import sys
    import os
    
    # Add src to path and run the new main
    sys.path.insert(0, os.path.dirname(__file__))
    from src.claw_face.main import main
    sys.exit(main())
