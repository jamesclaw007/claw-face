"""ClawFace - Main face controller with behaviors."""

import random
import time

import pygame

from .components import Eye, Mouth, StatusDisplay
from .config import Config


# Named expression presets: (mouth_expression, mouth_open, mouth_width, eye_squint, eye_size)
EXPRESSIONS = {
    "happy": (0.8, 0.0, 1.0, 0.0, 1.0),
    "very_happy": (1.0, 0.0, 1.2, 0.8, 1.0),
    "content": (0.5, 0.0, 0.8, 0.4, 1.0),
    "neutral": (0.15, 0.0, 0.9, 0.0, 1.0),
    "surprised": (0.2, 0.7, 0.8, 0.0, 1.2),
    "excited": (0.9, 0.3, 1.1, 0.0, 1.1),
    "sleepy": (0.3, 0.0, 0.7, 0.6, 0.85),
    "wink_happy": (0.9, 0.0, 1.0, 0.5, 1.0),  # + wink on one eye
}

# Weights for random expression selection (mostly positive expressions)
EXPRESSION_WEIGHTS = {
    "happy": 30,
    "very_happy": 15,
    "content": 20,
    "neutral": 10,
    "surprised": 5,
    "excited": 8,
    "sleepy": 7,
    "wink_happy": 5,
}


class ClawFace:
    """Main face class that orchestrates all components."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()

        pygame.init()

        # Set up display
        if self.config.display.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.width, self.height = self.screen.get_size()
        else:
            self.width = self.config.display.window_width
            self.height = self.config.display.window_height
            self.screen = pygame.display.set_mode((self.width, self.height))

        pygame.display.set_caption("Claw Face")

        # Calculate face dimensions
        screen_min = min(self.width, self.height)
        face_center_x = self.width // 2
        face_center_y = self.height // 2

        # Eye positioning
        eye_spacing = screen_min * 0.18
        eye_size = screen_min * 0.12
        eye_y_offset = screen_min * -0.05

        # Create eyes
        self.left_eye = Eye(
            face_center_x - eye_spacing,
            face_center_y + eye_y_offset,
            eye_size,
            self.config.colors,
        )
        self.right_eye = Eye(
            face_center_x + eye_spacing,
            face_center_y + eye_y_offset,
            eye_size,
            self.config.colors,
        )

        # Create mouth
        self.mouth = Mouth(
            face_center_x,
            face_center_y + eye_size * 1.5,
            eye_spacing * 1.5,
            self.config.colors,
        )

        # Face geometry
        self.face_center = (face_center_x, face_center_y)
        self.face_radius = int(screen_min * self.config.display.face_radius_ratio)

        # Status display
        self.status = StatusDisplay(self.width, self.height, self.config.colors)

        # Behavior timers
        self._reset_timers()

        # Current expression name (for wink logic)
        self._current_expression = "happy"

        self.clock = pygame.time.Clock()
        self.running = True

    def _reset_timers(self) -> None:
        """Reset all behavior timers."""
        now = time.time()
        behavior = self.config.behavior

        self.last_blink_time = now
        self.next_blink_interval = random.uniform(
            behavior.blink_interval_min, behavior.blink_interval_max
        )

        self.last_look_time = now
        self.next_look_interval = random.uniform(
            behavior.look_interval_min, behavior.look_interval_max
        )

        self.last_expression_time = now
        self.next_expression_interval = random.uniform(
            behavior.expression_interval_min, behavior.expression_interval_max
        )

    def handle_events(self) -> None:
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.blink()
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()

    def blink(self) -> None:
        """Trigger a blink on both eyes."""
        self.left_eye.start_blink()
        self.right_eye.start_blink()

    def look_at(self, x: float, y: float) -> None:
        """Make both eyes look at a direction (-1 to 1 range)."""
        self.left_eye.look_at(x, y)
        self.right_eye.look_at(x, y)

    def set_expression(self, name: str) -> None:
        """Set a named expression preset."""
        if name not in EXPRESSIONS:
            return

        mouth_expr, mouth_open, mouth_width, eye_squint, eye_size = EXPRESSIONS[name]

        self.mouth.set_expression(mouth_expr, mouth_open, mouth_width)
        self.left_eye.set_squint(eye_squint)
        self.right_eye.set_squint(eye_squint)
        self.left_eye.set_size(eye_size)
        self.right_eye.set_size(eye_size)

        # Handle wink expressions
        is_wink = name == "wink_happy"
        self.right_eye.set_wink(is_wink)
        if not is_wink:
            self.left_eye.set_wink(False)

        self._current_expression = name

    def update_behaviors(self) -> None:
        """Update autonomous behaviors based on timers."""
        now = time.time()
        behavior = self.config.behavior

        # Natural blinking
        if now - self.last_blink_time > self.next_blink_interval:
            self.blink()
            self.last_blink_time = now

            if random.random() < behavior.double_blink_chance:
                self.next_blink_interval = 0.3
            else:
                self.next_blink_interval = random.uniform(
                    behavior.blink_interval_min, behavior.blink_interval_max
                )

        # Random eye movements
        if now - self.last_look_time > self.next_look_interval:
            if random.random() < behavior.look_center_chance:
                self.look_at(0, 0)
            else:
                self.look_at(
                    random.uniform(-1, 1),
                    random.uniform(-0.5, 0.5),
                )

            self.last_look_time = now
            self.next_look_interval = random.uniform(
                behavior.look_interval_min, behavior.look_interval_max
            )

        # Occasional expression changes
        if now - self.last_expression_time > self.next_expression_interval:
            # Weighted random expression selection
            names = list(EXPRESSION_WEIGHTS.keys())
            weights = [EXPRESSION_WEIGHTS[n] for n in names]
            chosen = random.choices(names, weights=weights, k=1)[0]
            self.set_expression(chosen)

            self.last_expression_time = now
            self.next_expression_interval = random.uniform(
                behavior.expression_interval_min, behavior.expression_interval_max
            )

    def update(self) -> None:
        """Update all face components."""
        self.handle_events()
        self.update_behaviors()

        dt = self.clock.get_time() / 1000.0  # ms to seconds

        self.left_eye.update(dt)
        self.right_eye.update(dt)
        self.mouth.update(dt)
        self.status.update()

    def draw(self) -> None:
        """Draw the complete face."""
        colors = self.config.colors

        # Clear screen (black for LED look)
        self.screen.fill(colors.background)

        # Draw face components (dot-matrix style)
        self.left_eye.draw(self.screen)
        self.right_eye.draw(self.screen)
        self.mouth.draw(self.screen)

        # Draw status text
        self.status.draw(self.screen)

        # Update display
        pygame.display.flip()

    def run(self) -> None:
        """Main loop - run until ESC or Q is pressed."""
        while self.running:
            self.update()
            self.draw()
            self.clock.tick(self.config.display.fps)

        pygame.quit()
