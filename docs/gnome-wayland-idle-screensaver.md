# GNOME (Wayland): Show Claw Face When Idle, Lock On ESC

GNOME on Wayland does not support replacing the lock screen with a custom program. The approach here is:

1. Run a small user daemon that watches GNOME idle time (DBus: `org.gnome.Mutter.IdleMonitor`)
2. When you become idle, it launches Claw Face fullscreen
3. When you exit Claw Face (ESC/Q), it locks GNOME (DBus: `org.gnome.ScreenSaver.Lock`)

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

Wait 10 seconds without input. Claw Face should appear. Press `ESC` to exit, then GNOME should lock.

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

## GNOME Lock Settings

If GNOME auto-lock triggers before you press `ESC`, turn it off or increase the delay in:

`Settings -> Privacy -> Screen Lock`

## Tuning

- Idle time:
  - Default is `auto` (uses GNOME’s `org.gnome.desktop.session idle-delay`)
  - If GNOME `idle-delay` is `0` ("never"), `auto` falls back to `300` seconds
  - Override with `--idle-seconds 300` etc.
- Avoid port conflicts:
  - Use `--port 0` (ephemeral) to prevent collisions with another `claw-face` instance
