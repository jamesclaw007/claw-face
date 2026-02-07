# Claw Face (Repo Instructions)

This repo is a Python app that renders an animated dot-matrix “face” in a fullscreen `pywebview` window.

## Commands

- Run normally (fullscreen by default):
  - `claw-face`
  - or `PYTHONPATH=src python3 -m claw_face.main`
- Run windowed:
  - `claw-face --windowed`
- Run the GNOME/Wayland idle launcher (shows Claw Face when idle, locks on ESC/Q exit):
  - `claw-face-idle --idle-seconds auto --port 0`
  - `--port 0` uses an ephemeral port to avoid conflicts.
  - If GNOME idle delay is set to "never" (`idle-delay=0`), `auto` uses `300` seconds.

## GNOME Wayland “Screensaver” Behavior

GNOME on Wayland can’t replace the lock screen with a custom program. The supported setup here is:

1. Watch GNOME idle via DBus (`org.gnome.Mutter.IdleMonitor`)
2. Launch Claw Face fullscreen when idle
3. When Claw Face exits (ESC/Q), lock the session via DBus (`org.gnome.ScreenSaver.Lock`)

Docs: `docs/gnome-wayland-idle-screensaver.md`

## systemd (User Service)

Service template: `extras/systemd/claw-face-idle.service`

Install/enable (user):

```bash
pip install -e . --user
mkdir -p ~/.config/systemd/user
cp -a extras/systemd/claw-face-idle.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claw-face-idle.service
```

Operate:

- Status: `systemctl --user status claw-face-idle.service`
- Logs: `journalctl --user -u claw-face-idle.service -f`
- Stop: `systemctl --user stop claw-face-idle.service`

## Dev Notes

- If you use `--port 0`, the HTTP server binds an ephemeral port; the UI prints the resolved URL.
- Quick sanity check: `python3 -m compileall -q src`
