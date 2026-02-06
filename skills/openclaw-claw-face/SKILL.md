---
name: claw-face-display
description: Control the Claw Face kiosk display (expression + status line) for OpenClaw.
metadata: {"openclaw":{"requires":{"bins":["bash","python3"]}}}
---

# Claw Face Display (OpenClaw Skill)

This skill controls the `claw-face` kiosk UI by writing:

- `~/.config/claw-face/command.json` (expression + auto-cycle)
- `~/.config/claw-face/status.txt` (bottom status line)

The running Claw Face app polls these once per second (command) and every ~7s (status).

## Valid Expressions

`neutral`, `happy`, `sad`, `angry`, `surprised`, `sleepy`, `wink`, `love`, `talking`

## How To Use

Set an expression and optionally disable auto-cycling:

```bash
python3 "{baseDir}/scripts/claw_face_cmd.py" --expression happy --auto-cycle false
```

Re-enable auto-cycling:

```bash
python3 "{baseDir}/scripts/claw_face_cmd.py" --auto-cycle true
```

Set the status line (shown at the bottom):

```bash
python3 "{baseDir}/scripts/claw_face_cmd.py" --status "Thinking about wiring..."
```

Clear the status line:

```bash
python3 "{baseDir}/scripts/claw_face_cmd.py" --clear-status
```

Quit the kiosk (only works if Claw Face is running and using its local HTTP server):

```bash
curl -fsS "http://127.0.0.1:8420/api/quit" >/dev/null || true
```

