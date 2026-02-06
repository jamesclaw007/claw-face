---
name: claw-face-auto
description: Automatically update the Claw Face kiosk based on OpenClaw gateway events.
metadata: { "openclaw": { "emoji": "😺", "events": ["gateway:startup", "agent:bootstrap", "command:new", "command:reset", "command:stop", "agent:error"], "requires": { "bins": ["node"] } } }
---

# Claw Face Auto

This hook drives the `claw-face` kiosk UI by writing:

- `~/.config/claw-face/command.json`
- `~/.config/claw-face/status.txt`

## Behavior

- On `gateway:startup` / `agent:bootstrap`: set `neutral`, enable auto-cycle, status `Ready`.
- On `command:new`: set `talking`, disable auto-cycle, status `Working...` (best-effort).
- On `command:reset` / `command:stop`: return to idle (`neutral`/`sleepy`) and re-enable auto-cycle.
- On `agent:error`: set `sad`, disable auto-cycle, status `Error`.

Because not all OpenClaw builds emit fine-grained events for “reply complete”, the hook also schedules a short idle fallback after a command starts (so the face doesn’t get stuck in `talking` forever).
