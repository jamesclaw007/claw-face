"""Face components - Dot-matrix LED style Eye, Mouth, and StatusDisplay."""

import math
import time
from pathlib import Path

import pygame

from .config import Colors


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


def _ease_in_out(t: float) -> float:
    """Smooth ease in-out curve."""
    return t * t * (3 - 2 * t)


class DotMatrixEye:
    """Eye rendered as a circle of dots (LED dot-matrix style).

    Supports multiple states:
    - Normal: filled circle of dots
    - Happy/squint: curved arc shape (like upside-down U)
    - Blink: smooth close/open sequence
    - Wink: one eye closed as a line
    - Size changes: wide (surprised) or small (squint)
    """

    def __init__(self, center_x: float, center_y: float, size: float, colors: Colors):
        self.center_x = center_x
        self.center_y = center_y
        self.size = size
        self.colors = colors

        # Dot grid parameters
        self.dot_radius = max(2, int(size * 0.08))
        self.dot_spacing = self.dot_radius * 2.5

        # Pre-generate dot grids at various radii for size transitions
        self.base_dots = self._generate_circle_dots(size * 0.85)

        # Current look direction (-1 to 1)
        self.look_x = 0.0
        self.look_y = 0.0
        self.target_look_x = 0.0
        self.target_look_y = 0.0

        # Blink state (0 = open, 1 = closed)
        self.blink_amount = 0.0
        self.is_blinking = False
        self.blink_phase = 0.0  # 0..1 for close, 1..2 for hold, 2..3 for open
        self.blink_duration = 0.15  # seconds for each phase

        # Wink state
        self.is_winking = False

        # Happy/squint state (0 = normal circle, 1 = full happy arc)
        self.squint = 0.0
        self.target_squint = 0.0

        # Size multiplier (1.0 = normal, >1 = wide/surprised, <1 = small)
        self.size_mult = 1.0
        self.target_size_mult = 1.0

        # Movement smoothing
        self.look_speed = 0.12
        self.squint_speed = 0.08
        self.size_speed = 0.1

        # Timestamp for blink timing
        self._blink_start = 0.0

    def _generate_circle_dots(self, radius: float) -> list:
        """Generate dot positions that form a filled circle."""
        dots = []
        grid_range = int(radius / self.dot_spacing) + 1

        for row in range(-grid_range, grid_range + 1):
            for col in range(-grid_range, grid_range + 1):
                x = col * self.dot_spacing
                y = row * self.dot_spacing
                if x * x + y * y <= radius * radius:
                    dots.append((x, y))
        return dots

    def update(self, dt: float) -> None:
        """Update eye state."""
        # Smooth look movement
        self.look_x += (self.target_look_x - self.look_x) * self.look_speed
        self.look_y += (self.target_look_y - self.look_y) * self.look_speed

        # Smooth squint
        self.squint += (self.target_squint - self.squint) * self.squint_speed

        # Smooth size
        self.size_mult += (self.target_size_mult - self.size_mult) * self.size_speed

        # Blink animation (time-based for consistent speed)
        if self.is_blinking:
            elapsed = time.time() - self._blink_start
            total_duration = self.blink_duration * 2.5  # close + brief hold + open
            if elapsed >= total_duration:
                self.blink_amount = 0.0
                self.is_blinking = False
            else:
                progress = elapsed / total_duration
                if progress < 0.35:
                    # Closing phase
                    self.blink_amount = _ease_in_out(progress / 0.35)
                elif progress < 0.5:
                    # Hold closed
                    self.blink_amount = 1.0
                else:
                    # Opening phase
                    self.blink_amount = 1.0 - _ease_in_out((progress - 0.5) / 0.5)

    def start_blink(self) -> None:
        """Start a blink animation."""
        if not self.is_blinking and not self.is_winking:
            self.is_blinking = True
            self._blink_start = time.time()

    def look_at(self, x: float, y: float) -> None:
        """Set look direction (-1 to 1)."""
        self.target_look_x = max(-1, min(1, x))
        self.target_look_y = max(-1, min(1, y))

    def set_wink(self, winking: bool) -> None:
        """Set wink state (for one eye only)."""
        self.is_winking = winking

    def set_squint(self, amount: float) -> None:
        """Set happy/squint amount (0 = normal, 1 = full happy arc)."""
        self.target_squint = max(0, min(1, amount))

    def set_size(self, mult: float) -> None:
        """Set size multiplier (1.0 = normal)."""
        self.target_size_mult = max(0.7, min(1.3, mult))

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the dot-matrix eye."""
        look_offset_x = self.look_x * self.size * 0.15
        look_offset_y = self.look_y * self.size * 0.1

        effective_blink = 1.0 if self.is_winking else self.blink_amount

        # Fully closed - draw a horizontal line of dots
        if effective_blink > 0.95:
            dot_count = max(3, int(5 * self.size_mult))
            for i in range(-dot_count, dot_count + 1):
                x = int(self.center_x + i * self.dot_spacing * 0.8 + look_offset_x)
                y = int(self.center_y)
                pygame.draw.circle(screen, self.colors.eye_white, (x, y), self.dot_radius)
            return

        # Happy/squint arc mode
        if self.squint > 0.3 and effective_blink < 0.1:
            self._draw_happy_arc(screen, look_offset_x, look_offset_y)
            return

        # Blend between normal and slightly squinted
        self._draw_normal(screen, look_offset_x, look_offset_y, effective_blink)

    def _draw_happy_arc(self, screen: pygame.Surface, offset_x: float, offset_y: float) -> None:
        """Draw a happy curved-arc eye (like an upside-down U)."""
        radius = self.size * 0.85 * self.size_mult
        # Arc spans about 180 degrees across the bottom
        arc_dots = max(8, int(radius / self.dot_spacing) * 4)

        # Blend between full circle and arc based on squint amount
        # At squint=1, the arc is a tight upside-down U
        arc_span = math.pi * (0.55 + 0.25 * self.squint)  # ~100° to ~145°
        start_angle = math.pi / 2 - arc_span / 2  # centered on top

        # Draw multiple concentric arcs for thickness
        thickness_steps = max(2, int(radius * 0.35 / self.dot_spacing))
        for ring in range(thickness_steps):
            r = radius * (0.65 + 0.35 * ring / max(1, thickness_steps - 1))
            for i in range(arc_dots + 1):
                t = i / arc_dots
                angle = start_angle + t * arc_span
                x = int(self.center_x + math.cos(angle) * r + offset_x)
                # Flip Y so the arc opens downward (happy eyes)
                y = int(self.center_y - math.sin(angle) * r * 0.8 + offset_y)
                pygame.draw.circle(screen, self.colors.eye_white, (x, y), self.dot_radius)

    def _draw_normal(self, screen: pygame.Surface, offset_x: float, offset_y: float,
                     blink: float) -> None:
        """Draw normal circular eye with blink compression."""
        effective_radius = self.size * 0.85 * self.size_mult
        vertical_scale = 1.0 - blink * 0.85

        # Use squint to slightly flatten even in normal mode (partial squint)
        if self.squint > 0.05:
            vertical_scale *= (1.0 - self.squint * 0.4)

        grid_range = int(effective_radius / self.dot_spacing) + 1

        for row in range(-grid_range, grid_range + 1):
            for col in range(-grid_range, grid_range + 1):
                dot_x = col * self.dot_spacing
                dot_y = row * self.dot_spacing

                # Check circle membership at current size
                if dot_x * dot_x + dot_y * dot_y > effective_radius * effective_radius:
                    continue

                # Apply blink/squint compression
                compressed_y = dot_y * vertical_scale

                # Clip dots that escape during blink
                max_y = effective_radius * (1 - blink * 0.5)
                if abs(compressed_y) > max_y:
                    continue

                x = int(self.center_x + dot_x + offset_x)
                y = int(self.center_y + compressed_y + offset_y)

                pygame.draw.circle(screen, self.colors.eye_white, (x, y), self.dot_radius)


class DotMatrixMouth:
    """Mouth rendered with dot-matrix style."""

    def __init__(self, center_x: float, center_y: float, width: float, colors: Colors):
        self.center_x = center_x
        self.center_y = center_y
        self.width = width
        self.colors = colors

        # Dot parameters matching eye style
        dot_base = width * 0.025
        self.dot_radius = max(2, int(dot_base))
        self.dot_spacing = self.dot_radius * 2.5

        # Expression: -1 = sad, 0 = neutral, 1 = happy
        self.expression = 0.5
        self.target_expression = 0.5

        # Open amount for surprised/talking look (0 to 1)
        self.open_amount = 0.0
        self.target_open = 0.0

        # Mouth width multiplier (for grin vs small smile)
        self.width_mult = 1.0
        self.target_width_mult = 1.0

        self.expression_speed = 0.08
        self.open_speed = 0.1
        self.width_speed = 0.08

    def update(self, dt: float) -> None:
        """Update mouth state."""
        self.expression += (self.target_expression - self.expression) * self.expression_speed
        self.open_amount += (self.target_open - self.open_amount) * self.open_speed
        self.width_mult += (self.target_width_mult - self.width_mult) * self.width_speed

    def set_expression(self, expression: float, open_amount: float = 0.0,
                       width_mult: float = 1.0) -> None:
        """Set expression (-1 to 1), open amount (0 to 1), width (0.5 to 1.5)."""
        self.target_expression = max(-1, min(1, expression))
        self.target_open = max(0, min(1, open_amount))
        self.target_width_mult = max(0.5, min(1.5, width_mult))

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the dot-matrix mouth."""
        if self.open_amount > 0.3:
            self._draw_open_mouth(screen)
        else:
            self._draw_curve_mouth(screen)

    def _draw_curve_mouth(self, screen: pygame.Surface) -> None:
        """Draw a curved smile/frown line of dots."""
        half_w = (self.width / 2) * self.width_mult
        curve_height = self.expression * self.width * 0.15

        # Number of dots along the curve
        dot_count = max(7, int(half_w * 2 / self.dot_spacing))

        # Draw main curve as dots
        for i in range(dot_count + 1):
            t = i / dot_count
            x = self.center_x - half_w + t * half_w * 2

            # Quadratic curve: deepest in center
            normalized = 2 * t - 1  # -1 to 1
            curve_offset = curve_height * (1 - normalized * normalized)
            y = self.center_y + curve_offset

            # Slight blend of open amount as vertical offset at center
            if self.open_amount > 0.05:
                open_push = self.open_amount * 3 * (1 - normalized * normalized)
                y += open_push

            pygame.draw.circle(screen, self.colors.mouth,
                               (int(x), int(y)), self.dot_radius)

        # For bigger smiles, add a second row of dots for thickness
        if abs(self.expression) > 0.5:
            thickness_offset = self.dot_spacing * 0.7
            sign = 1 if self.expression > 0 else -1
            for i in range(dot_count + 1):
                t = i / dot_count
                x = self.center_x - half_w + t * half_w * 2
                normalized = 2 * t - 1
                # Only thicken the middle portion
                if abs(normalized) > 0.75:
                    continue
                curve_offset = curve_height * (1 - normalized * normalized)
                y = self.center_y + curve_offset + thickness_offset * sign

                pygame.draw.circle(screen, self.colors.mouth,
                                   (int(x), int(y)), self.dot_radius)

    def _draw_open_mouth(self, screen: pygame.Surface) -> None:
        """Draw an open mouth (ellipse of dots) for surprised/talking."""
        open_w = self.width * 0.25 * self.width_mult
        open_h = self.open_amount * self.width * 0.25

        # Offset based on expression curve
        curve_y_offset = self.expression * self.width * 0.06

        cx = self.center_x
        cy = self.center_y + curve_y_offset

        # Draw ellipse outline as dots
        dot_count = max(12, int((open_w + open_h) * 2 / self.dot_spacing))
        for i in range(dot_count):
            angle = 2 * math.pi * i / dot_count
            x = cx + math.cos(angle) * open_w
            y = cy + math.sin(angle) * open_h
            pygame.draw.circle(screen, self.colors.mouth,
                               (int(x), int(y)), self.dot_radius)


# Use DotMatrixMouth as the default Mouth
class Mouth(DotMatrixMouth):
    """Backward-compatible Mouth alias."""
    pass


class StatusDisplay:
    """Displays project status text at the bottom of the screen."""

    STATUS_PATH = Path.home() / ".config" / "claw-face" / "status.txt"
    CHECK_INTERVAL = 7.0

    def __init__(self, screen_w: int, screen_h: int, colors: Colors):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.colors = colors
        self.text = ""
        self.last_check = 0.0
        self.alpha = 0.0
        self.target_alpha = 0.0

        pygame.font.init()
        font_size = max(16, int(screen_h * 0.022))
        self.font = pygame.font.SysFont("monospace", font_size)

    def update(self) -> None:
        """Check file and update display state."""
        now = time.time()

        if now - self.last_check > self.CHECK_INTERVAL:
            self.last_check = now
            self._read_status()

        self.alpha += (self.target_alpha - self.alpha) * 0.05

    def _read_status(self) -> None:
        """Read status text from the config file."""
        try:
            if self.STATUS_PATH.exists():
                content = self.STATUS_PATH.read_text().strip()
                if content:
                    self.text = content
                    self.target_alpha = 1.0
                else:
                    self.text = ""
                    self.target_alpha = 0.0
            else:
                self.text = ""
                self.target_alpha = 0.0
        except OSError:
            pass

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the status text at the bottom of the screen."""
        if not self.text or self.alpha < 0.02:
            return

        alpha_int = int(self.alpha * 120)

        display_str = f"Working on: {self.text}"
        text_surface = self.font.render(display_str, True, (180, 180, 190))
        text_surface.set_alpha(alpha_int)

        text_rect = text_surface.get_rect(
            center=(self.screen_w // 2, self.screen_h - int(self.screen_h * 0.04))
        )
        screen.blit(text_surface, text_rect)


# Keep Eye as alias for compatibility
Eye = DotMatrixEye
