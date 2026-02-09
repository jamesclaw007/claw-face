# GNOME (Wayland): Show Claw Face When Idle

A small user daemon watches GNOME idle time (DBus: `org.gnome.Mutter.IdleMonitor`) and launches Claw Face fullscreen when you become idle. When you exit Claw Face (ESC/Q), the idle timer resets and the cycle begins again.

## Install

From the repo:

```bash
cd ~/Projects/claw-face
pip install -e . --user
```

## Try It Manually

```bash
claw-face-idle --idle-seconds 10 --port 0
```

Wait 10 seconds without input. Claw Face should appear. Press `ESC` to exit; the idle timer resets.

## Enable At Login (systemd --user)

1. Install the service file:

```bash
mkdir -p ~/.config/systemd/user
cp -a extras/systemd/claw-face-idle.service ~/.config/systemd/user/
```

2. Enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now claw-face-idle.service
```

3. Check logs:

```bash
journalctl --user -u claw-face-idle.service -f
```

## Tuning

- Idle time:
  - Default is `auto` (uses GNOME’s `org.gnome.desktop.session idle-delay`)
  - If GNOME `idle-delay` is `0` ("never"), `auto` falls back to `300` seconds
  - Override with `--idle-seconds 300` etc.
- Avoid port conflicts:
  - Use `--port 0` (ephemeral) to prevent collisions with another `claw-face` instance
