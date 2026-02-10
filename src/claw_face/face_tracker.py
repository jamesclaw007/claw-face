"""Face tracking daemon for Claw Face.

Uses the webcam to detect faces and sends gaze coordinates to Claw Face
via the command.json file, making the eyes follow nearby people.

Usage:
    python -m claw_face.face_tracker [--device 0] [--interval 0.15]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import signal
import sys
import tempfile
import time
from pathlib import Path

import cv2


def get_command_path() -> Path:
    """Return the path to the Claw Face command.json file."""
    return Path.home() / ".config" / "claw-face" / "command.json"


def get_status_path() -> Path:
    """Return the path to the Claw Face status.txt file."""
    return Path.home() / ".config" / "claw-face" / "status.txt"


# Greeting messages when a face is detected
GREETINGS = [
    "Hi! I see you!",
    "Oh hey there!",
    "Hello!",
    "I see you!",
    "Hi there!",
    "Hey! :)",
]


def atomic_write(path: Path, data: str) -> None:
    """Write data to file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        os.write(fd, data.encode())
        os.close(fd)
        os.replace(tmp, str(path))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_current_command(path: Path) -> dict:
    """Read current command.json, return empty dict on failure."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def write_look(path: Path, x: float, y: float, current_cmd: dict) -> None:
    """Update command.json with look override, preserving other fields."""
    cmd = dict(current_cmd)
    cmd["look"] = {"x": round(x, 3), "y": round(y, 3)}
    atomic_write(path, json.dumps(cmd, indent=2) + "\n")


def clear_look(path: Path, current_cmd: dict) -> None:
    """Remove look override from command.json."""
    cmd = dict(current_cmd)
    cmd.pop("look", None)
    atomic_write(path, json.dumps(cmd, indent=2) + "\n")


def write_status(path: Path, text: str) -> None:
    """Write status text to status.txt."""
    atomic_write(path, text + "\n" if text else "")


def read_status(path: Path) -> str:
    """Read current status text."""
    try:
        return path.read_text().strip()
    except Exception:
        return ""


def map_face_to_gaze(face_cx: float, face_cy: float,
                      frame_w: int, frame_h: int) -> tuple[float, float]:
    """Map face position in frame to gaze coordinates (-1 to 1).

    The webcam is usually above the screen, so the face appears in the
    camera's view roughly centered. We map the face position to gaze
    direction — if the person is to the left of the camera, the eyes
    should look left (toward them).

    Note: webcam image is typically mirrored, so we flip X.
    Y is inverted: face at top of frame → person is above → look up.
    """
    # Normalize to -1..1
    nx = (face_cx / frame_w) * 2 - 1
    ny = (face_cy / frame_h) * 2 - 1

    # Mirror X (webcam is mirrored)
    gaze_x = -nx

    # Invert Y: face at top of frame means person is up
    gaze_y = -ny

    # Dampen to keep it natural (don't max out at edges)
    gaze_x = max(-0.8, min(0.8, gaze_x * 1.2))
    gaze_y = max(-0.5, min(0.5, gaze_y * 0.8))

    return gaze_x, gaze_y


def run_tracker(device: int = 0, interval: float = 0.15,
                 scale: float = 0.3) -> None:
    """Main tracking loop."""
    # Primary: face detection (multiple cascades for robustness)
    face_cascades = []
    for name in ["haarcascade_frontalface_alt2.xml",
                 "haarcascade_frontalface_default.xml",
                 "haarcascade_profileface.xml"]:
        c = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        if not c.empty():
            face_cascades.append((name, c))

    # Fallback: upper body detection (works when face is obscured)
    body_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_upperbody.xml"
    )

    if not face_cascades and body_cascade.empty():
        print("ERROR: Could not load any cascade classifiers", file=sys.stderr)
        sys.exit(1)

    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        print(f"ERROR: Could not open camera device {device}", file=sys.stderr)
        sys.exit(1)

    # Lower resolution for speed
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    cmd_path = get_command_path()
    status_path = get_status_path()
    print(f"Face tracker started (device={device}, interval={interval}s)")
    print(f"Cascades loaded: {[n for n,_ in face_cascades]}")
    print(f"Body fallback: {'yes' if not body_cascade.empty() else 'no'}")
    print(f"Command path: {cmd_path}")

    running = True

    def handle_signal(sig, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    last_gaze_x, last_gaze_y = 0.0, 0.0
    smoothing = 0.4  # lower = smoother, higher = more responsive
    no_face_count = 0
    NO_FACE_THRESHOLD = 8  # frames without face before clearing look
    tracking_active = False  # whether we're currently tracking someone
    TRACKER_STATUS_PREFIX = "👀 "  # prefix to identify our status messages

    try:
        while running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(interval)
                continue

            # Downscale for faster detection
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (int(w * scale), int(h * scale)))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            # Try face detection with each cascade
            faces = []
            for _name, cascade in face_cascades:
                faces = cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(int(20 * scale), int(20 * scale)),
                    flags=cv2.CASCADE_SCALE_IMAGE,
                )
                if len(faces) > 0:
                    break

            # Fallback to upper body if no face found
            is_body = False
            if len(faces) == 0 and not body_cascade.empty():
                faces = body_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.05,
                    minNeighbors=2,
                    minSize=(int(30 * scale), int(30 * scale)),
                    flags=cv2.CASCADE_SCALE_IMAGE,
                )
                is_body = len(faces) > 0

            current_cmd = read_current_command(cmd_path)

            if len(faces) > 0:
                no_face_count = 0

                # Use the largest detection (closest person)
                areas = [fw * fh for (_, _, fw, fh) in faces]
                best = max(range(len(faces)), key=lambda i: areas[i])
                fx, fy, fw, fh = faces[best]

                # Scale back to original frame coordinates
                cx = (fx + fw / 2) / scale
                # For body detection, estimate face position (upper third)
                if is_body:
                    cy = (fy + fh * 0.25) / scale
                else:
                    cy = (fy + fh / 2) / scale

                target_x, target_y = map_face_to_gaze(cx, cy, w, h)

                # Smooth the gaze to avoid jitter
                last_gaze_x += (target_x - last_gaze_x) * smoothing
                last_gaze_y += (target_y - last_gaze_y) * smoothing

                write_look(cmd_path, last_gaze_x, last_gaze_y, current_cmd)

                # Show greeting when we first detect someone
                if not tracking_active:
                    tracking_active = True
                    greeting = random.choice(GREETINGS)
                    write_status(status_path, greeting)
                    print(f"Face detected — {greeting}")

            else:
                no_face_count += 1
                if no_face_count >= NO_FACE_THRESHOLD:
                    # No face for a while — clear the look override
                    if "look" in current_cmd:
                        clear_look(cmd_path, current_cmd)
                    last_gaze_x, last_gaze_y = 0.0, 0.0

                    # Clear our greeting if it's still showing
                    if tracking_active:
                        tracking_active = False
                        cur_status = read_status(status_path)
                        if cur_status in GREETINGS:
                            write_status(status_path, "")
                            print("Face lost — cleared greeting")

            time.sleep(interval)

    finally:
        cap.release()
        # Clean up look override and status on exit
        try:
            current_cmd = read_current_command(cmd_path)
            if "look" in current_cmd:
                clear_look(cmd_path, current_cmd)
            cur_status = read_status(status_path)
            if cur_status in GREETINGS:
                write_status(status_path, "")
        except Exception:
            pass
        print("Face tracker stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Claw Face webcam face tracker")
    parser.add_argument("--device", type=int, default=0,
                        help="Camera device index (default: 0)")
    parser.add_argument("--interval", type=float, default=0.15,
                        help="Seconds between captures (default: 0.15)")
    parser.add_argument("--scale", type=float, default=0.3,
                        help="Frame downscale factor for detection (default: 0.3)")
    args = parser.parse_args()
    run_tracker(device=args.device, interval=args.interval, scale=args.scale)


if __name__ == "__main__":
    main()
