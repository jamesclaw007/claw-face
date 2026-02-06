#!/usr/bin/env python3
"""
GNOME/Wayland idle launcher for Claw Face.

Runs as a user daemon:
- Wait for GNOME idle (via org.gnome.Mutter.IdleMonitor)
- Launch Claw Face fullscreen when idle
- After Claw Face exits (ESC/Q), lock the session (org.gnome.ScreenSaver)
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Optional


def _require_gi() -> None:
    try:
        import gi  # noqa: F401
    except Exception as e:  # pragma: no cover
        print(
            "claw-face-idle requires PyGObject (gi) on Linux.\n"
            "On Fedora: sudo dnf install -y python3-gobject\n"
            f"Import error: {e}",
            file=sys.stderr,
        )
        raise SystemExit(2)


_require_gi()
from gi.repository import Gio, GLib  # noqa: E402


@dataclass(frozen=True)
class Settings:
    idle_seconds: int
    lock_on_exit: bool
    face_port: int
    face_args: list[str]


def _get_idle_seconds_from_gsettings() -> int:
    # org.gnome.desktop.session idle-delay is uint32 seconds.
    try:
        s = Gio.Settings.new("org.gnome.desktop.session")
        v = int(s.get_uint("idle-delay"))
        # GNOME uses 0 to mean "never". For our daemon, treat it as a reasonable default
        # rather than launching immediately.
        if v <= 0:
            return 300
        return v
    except Exception:
        # Fall back to something sane if gsettings isn't accessible.
        return 300


def _proxy(bus_name: str, object_path: str, interface: str) -> Gio.DBusProxy:
    return Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.NONE,
        None,
        bus_name,
        object_path,
        interface,
        None,
    )


def _dbus_call(proxy: Gio.DBusProxy, method: str, params: Optional[GLib.Variant] = None):
    return proxy.call_sync(method, params, Gio.DBusCallFlags.NONE, -1, None)


def _screensaver_get_active(screensaver: Gio.DBusProxy) -> bool:
    try:
        out = _dbus_call(screensaver, "GetActive", None)
        return bool(out.unpack()[0])
    except Exception:
        return False


def _screensaver_lock(screensaver: Gio.DBusProxy) -> bool:
    try:
        _dbus_call(screensaver, "Lock", None)
        return True
    except Exception:
        return False


def _fallback_lock() -> None:
    # Try a couple of best-effort fallbacks if the GNOME screensaver DBus API is unavailable.
    for cmd in (["loginctl", "lock-session"], ["gnome-screensaver-command", "-l"]):
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue


class IdleDaemon:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.idle = _proxy(
            "org.gnome.Mutter.IdleMonitor",
            "/org/gnome/Mutter/IdleMonitor/Core",
            "org.gnome.Mutter.IdleMonitor",
        )
        self.screensaver = _proxy(
            "org.gnome.ScreenSaver",
            "/org/gnome/ScreenSaver",
            "org.gnome.ScreenSaver",
        )

        self._loop = GLib.MainLoop()
        self._idle_watch_id: Optional[int] = None
        self._user_active_watch_id: Optional[int] = None
        self._face_proc: Optional[subprocess.Popen] = None
        self._exiting = False

    def _remove_watch(self, watch_id: Optional[int]) -> None:
        if watch_id is None:
            return
        try:
            _dbus_call(self.idle, "RemoveWatch", GLib.Variant("(u)", (int(watch_id),)))
        except Exception:
            pass

    def _set_idle_watch(self) -> None:
        # Remove any previous watch (safety), then re-add.
        self._remove_watch(self._idle_watch_id)
        self._idle_watch_id = None

        interval_ms = int(self.settings.idle_seconds) * 1000
        out = _dbus_call(self.idle, "AddIdleWatch", GLib.Variant("(t)", (interval_ms,)))
        self._idle_watch_id = int(out.unpack()[0])

    def _set_user_active_watch(self) -> None:
        # Ensure we only have one outstanding active watch.
        self._remove_watch(self._user_active_watch_id)
        self._user_active_watch_id = None
        out = _dbus_call(self.idle, "AddUserActiveWatch", None)
        self._user_active_watch_id = int(out.unpack()[0])

    def _on_idle_signal(self, _proxy, _sender_name, signal_name, params) -> None:
        if signal_name != "WatchFired":
            return
        try:
            fired_id = int(params.unpack()[0])
        except Exception:
            return

        if self._exiting:
            return

        if self._idle_watch_id is not None and fired_id == self._idle_watch_id:
            # One-shot: remove this watch while we run.
            self._remove_watch(self._idle_watch_id)
            self._idle_watch_id = None
            GLib.idle_add(self._start_face_if_needed)
            return

        if self._user_active_watch_id is not None and fired_id == self._user_active_watch_id:
            self._remove_watch(self._user_active_watch_id)
            self._user_active_watch_id = None
            # After user activity (e.g., unlock), restart the idle countdown from "now".
            try:
                _dbus_call(self.idle, "ResetIdletime", None)
            except Exception:
                pass
            GLib.idle_add(self._set_idle_watch)
            return

    def _start_face_if_needed(self):
        if self._exiting:
            return GLib.SOURCE_REMOVE
        if self._face_proc is not None and self._face_proc.poll() is None:
            return GLib.SOURCE_REMOVE
        if _screensaver_get_active(self.screensaver):
            # Don't re-arm the idle watch while locked; wait until we see activity again.
            self._set_user_active_watch()
            return GLib.SOURCE_REMOVE

        cmd = [sys.executable, "-m", "claw_face.main"]
        cmd += ["--port", str(self.settings.face_port)]
        cmd += list(self.settings.face_args)

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        self._face_proc = subprocess.Popen(cmd, env=env)

        t = threading.Thread(target=self._wait_face_then_lock_and_rearm, daemon=True)
        t.start()
        return GLib.SOURCE_REMOVE

    def _wait_face_then_lock_and_rearm(self) -> None:
        proc = self._face_proc
        if proc is None:
            return
        try:
            proc.wait()
        finally:
            self._face_proc = None

        if self._exiting:
            return

        if self.settings.lock_on_exit:
            if not _screensaver_lock(self.screensaver):
                _fallback_lock()
            # After locking, wait for user activity (unlock) before re-arming idle watch.
            GLib.idle_add(self._set_user_active_watch)
        else:
            # If we didn't lock, restart the idle timer from "now".
            try:
                _dbus_call(self.idle, "ResetIdletime", None)
            except Exception:
                pass
            GLib.idle_add(self._set_idle_watch)

    def stop(self) -> None:
        self._exiting = True
        self._remove_watch(self._idle_watch_id)
        self._idle_watch_id = None
        self._remove_watch(self._user_active_watch_id)
        self._user_active_watch_id = None

        if self._face_proc is not None and self._face_proc.poll() is None:
            try:
                self._face_proc.terminate()
            except Exception:
                pass

        try:
            self._loop.quit()
        except Exception:
            pass

    def run(self) -> int:
        self._set_idle_watch()
        self.idle.connect("g-signal", self._on_idle_signal)

        def _handle_sig(_signum, _frame):
            self.stop()

        for s in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(s, _handle_sig)
            except Exception:
                pass

        self._loop.run()
        return 0


def _parse_args(argv: list[str]) -> Settings:
    p = argparse.ArgumentParser(
        prog="claw-face-idle",
        description="Launch Claw Face when GNOME reports idle; lock after exit.",
    )
    p.add_argument(
        "--idle-seconds",
        default="auto",
        help="Idle time before launching (seconds) or 'auto' to use GNOME idle-delay (default).",
    )
    p.add_argument(
        "--no-lock",
        action="store_true",
        help="Do not lock on Claw Face exit.",
    )
    p.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port to run Claw Face on (0 = ephemeral, recommended).",
    )
    p.add_argument(
        "face_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed to claw-face (prefix with '--', e.g. claw-face-idle -- --fps 20).",
    )

    a = p.parse_args(argv)

    if a.idle_seconds == "auto":
        idle_seconds = _get_idle_seconds_from_gsettings()
    else:
        try:
            idle_seconds = max(1, int(a.idle_seconds))
        except ValueError:
            raise SystemExit("--idle-seconds must be an integer or 'auto'")

    face_args = list(a.face_args)
    if face_args and face_args[0] == "--":
        face_args = face_args[1:]

    return Settings(
        idle_seconds=idle_seconds,
        lock_on_exit=not bool(a.no_lock),
        face_port=int(a.port),
        face_args=face_args,
    )


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    s = _parse_args(argv)
    d = IdleDaemon(s)
    return d.run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
