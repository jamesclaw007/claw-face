#!/bin/bash
# Launch Claw Face
cd "$(dirname "$0")"
exec env PYTHONPATH=src python3 -m claw_face "$@"
