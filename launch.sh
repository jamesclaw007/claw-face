#!/bin/bash
# Launch Claw Face
cd "$(dirname "$0")"
exec python3 -m src.claw_face.main "$@"
