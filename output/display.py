"""
Stelly's face.

Draws the eyes and mouth from face_shapes.py, geometry lifted straight
from Skyler's reference SVGs, colored by whichever palette is active
from themes.py. Everything scales uniformly to fit the current window,
same proportions whether that's the 480x480 HyperPixel or a much wider
desktop test window, nothing gets stretched out of shape to fill space,
it just centers with matching background on either side if the aspect
ratio does not match the reference art.

Drawing happens on an internal surface at SUPERSAMPLE times the reference
canvas resolution, then that gets smoothly downscaled onto the real
screen. pygame's basic draw calls (lines, polygon, ellipse) are not anti
aliased, drawn at 1:1 they come out jagged, especially on curves. Drawing
bigger and shrinking with a smooth filter is the standard trick to fake
anti aliasing without a heavier dependency.

Animation stays deliberately light: blinking on a random timer, a small
idle bob so it does not look like a static image, and a two frame mouth
flap while Stelly is speaking. Mood swaps between two mouth shapes drawn
from the reference art (closed smile, open gulp) and a mirrored frown
for anything sad.

The color theme follows the clock like a phone does, light during the
day, dark at night, with manual override until the next boundary.
"""

import math
import random
import time
from datetime import datetime

import pygame

from config import timekeeping
from output import face_shapes, themes

THEME_CHECK_SECONDS = 30  # how often the clock gets consulted for auto theme

SCREEN_SIZE = (480, 480)
SUPERSAMPLE = 2  # internal render scale, higher looks crisper but costs more per frame

BLINK_MIN_INTERVAL = 2.0
BLINK_MAX_INTERVAL = 6.0
BLINK_DURATION = 0.15

BOB_PERIOD_SECONDS = 4.0
BOB_AMPLITUDE_FRACTION = 0.015  # fraction of canvas height, kept small on purpose

TALK_FLAP_SECONDS = 0.16  # how long the mouth holds open or closed while talking

FRAME_RATE = 30

MOOD_EXPRESSIONS = {
    "neutral": "smile",
    "sleepy": "smile",
    "happy": "gulp",
    "excited": "gulp",
    "sad": "frown",
    "worried": "frown",
}
DEFAULT_MOOD = "neutral"


class Face:
    def __init__(self, screen_size=SCREEN_SIZE, theme=None):
        pygame.init()
        self.screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
        pygame.display.set_caption("Stelly")
        self.clock = pygame.time.Clock()
        self.width, self.height = screen_size

        canvas_w, canvas_h = face_shapes.CANVAS_SIZE
        self._canvas = pygame.Surface((canvas_w * SUPERSAMPLE, canvas_h * SUPERSAMPLE))

        self.mood = DEFAULT_MOOD
        self.talking = False

        # Theme follows the clock like a phone: light during the day,
        # dark at night. Passing an explicit theme, or pressing D, sets a
        # manual override that lasts until the next natural sunrise or
        # sunset boundary, then automatic switching resumes.
        self._override_until = None
        self._next_theme_check = 0.0
        if theme in themes.THEMES:
            self.theme_name = theme
            self._override_until = timekeeping.next_transition()
        else:
            self.theme_name = self._clock_theme()

        self.blinking = False
        self.blink_end_time = 0.0
        self.next_blink_time = time.time() + random.uniform(BLINK_MIN_INTERVAL, BLINK_MAX_INTERVAL)
        self.start_time = time.time()

    def set_mood(self, mood):
        """Switch expression. Unknown moods are ignored rather than
        crashing the display loop over a typo somewhere upstream."""
        if mood in MOOD_EXPRESSIONS:
            self.mood = mood

    def set_talking(self, talking):
        """Flip the mouth flap on or off. Safe to call from another
        thread, it is a single attribute write that the draw loop reads."""
        self.talking = bool(talking)

    def set_theme(self, theme_name):
        """Manually force a theme, held until the next day/night boundary."""
        if theme_name in themes.THEMES:
            self.theme_name = theme_name
            self._override_until = timekeeping.next_transition()

    def toggle_theme(self):
        self.set_theme("dark" if self.theme_name == "light" else "light")

    @staticmethod
    def _clock_theme():
        return "light" if timekeeping.is_daytime() else "dark"

    def _update_theme(self):
        """Follow the clock, cheaply. Consults the calendar clock only
        every THEME_CHECK_SECONDS rather than every frame, and respects a
        manual override until its boundary passes."""
        now = time.time()
        if now < self._next_theme_check:
            return
        self._next_theme_check = now + THEME_CHECK_SECONDS

        if self._override_until is not None:
            if datetime.now() < self._override_until:
                return
            self._override_until = None  # boundary passed, resume auto

        self.theme_name = self._clock_theme()

    @property
    def _theme(self):
        return themes.THEMES[self.theme_name]

    def _update_blink(self):
        now = time.time()
        if self.blinking and now >= self.blink_end_time:
            self.blinking = False
            self.next_blink_time = now + random.uniform(BLINK_MIN_INTERVAL, BLINK_MAX_INTERVAL)
        elif not self.blinking and now >= self.next_blink_time:
            self.blinking = True
            self.blink_end_time = now + BLINK_DURATION

    def _bob_offset(self, scale):
        """A small idle vertical drift so the face reads as alive without
        being distracting. Amplitude is tied to the reference canvas
        height so it scales down proportionally on smaller screens too."""
        canvas_h = face_shapes.CANVAS_SIZE[1]
        elapsed = time.time() - self.start_time
        phase = (elapsed % BOB_PERIOD_SECONDS) / BOB_PERIOD_SECONDS
        return math.sin(phase * 2 * math.pi) * canvas_h * BOB_AMPLITUDE_FRACTION * scale

    def _to_canvas(self, point):
        """Reference SVG coordinates to pixel coordinates on the internal
        supersampled surface. No offset needed here, letterboxing happens
        later when the finished canvas gets blitted onto the real screen."""
        x, y = point
        return (x * SUPERSAMPLE, y * SUPERSAMPLE)

    def _draw_eyes(self):
        color = self._theme["eye"]
        for eye in (face_shapes.EYE_LEFT, face_shapes.EYE_RIGHT):
            cx, cy = self._to_canvas((eye["cx"], eye["cy"]))
            rx, ry = eye["rx"] * SUPERSAMPLE, eye["ry"] * SUPERSAMPLE

            if self.blinking:
                thickness = max(2, int(ry * 0.35))
                pygame.draw.line(self._canvas, color, (cx - rx, cy), (cx + rx, cy), thickness)
            else:
                rect = pygame.Rect(0, 0, rx * 2, ry * 2)
                rect.center = (cx, cy)
                pygame.draw.ellipse(self._canvas, color, rect)

    def _draw_polygon(self, points, color):
        canvas_points = [self._to_canvas(p) for p in points]
        pygame.draw.polygon(self._canvas, color, canvas_points)

    def _draw_thick_open_path(self, points, color, width):
        """Draw an open (unfilled) path with a rounded stroke. pygame has
        no native variable width bezier stroke, so this draws the
        polyline plus a circle at every endpoint, which is what gives the
        reference art's round line caps instead of a hard square end."""
        canvas_points = [self._to_canvas(p) for p in points]
        line_width = max(1, int(width * SUPERSAMPLE))

        if len(canvas_points) >= 2:
            pygame.draw.lines(self._canvas, color, False, canvas_points, line_width)

        radius = line_width // 2
        if radius > 0:
            for point in (canvas_points[0], canvas_points[-1]):
                pygame.draw.circle(self._canvas, color, (int(point[0]), int(point[1])), radius)

    def _current_expression(self):
        """Which mouth to draw this frame. While talking, alternate
        between the open gulp mouth and the mood's resting mouth on a
        steady timer, a classic two frame mouth flap. When quiet, just
        the mood's resting mouth."""
        resting = MOOD_EXPRESSIONS[self.mood]
        if not self.talking:
            return resting
        elapsed = time.time() - self.start_time
        mouth_open = int(elapsed / TALK_FLAP_SECONDS) % 2 == 0
        if mouth_open:
            return "gulp"
        return resting if resting != "gulp" else "smile"

    def _draw_mouth(self):
        theme = self._theme
        expression = self._current_expression()

        if expression == "smile":
            self._draw_thick_open_path(face_shapes.SMILE_MOUTH_POINTS, theme["mouth_stroke"], face_shapes.SMILE_STROKE_WIDTH)
        elif expression == "frown":
            self._draw_thick_open_path(face_shapes.FROWN_MOUTH_POINTS, theme["mouth_stroke"], face_shapes.SMILE_STROKE_WIDTH)
        elif expression == "gulp":
            self._draw_polygon(face_shapes.GULP_DARK_FILL_POINTS, theme["mouth_dark_fill"])
            self._draw_polygon(face_shapes.GULP_LIGHT_HIGHLIGHT_POINTS, theme["mouth_light_fill"])
            self._draw_polygon(face_shapes.GULP_TEETH_RECT_POINTS, theme["mouth_teeth"])
            self._draw_thick_open_path(
                face_shapes.GULP_TEETH_RECT_POINTS + [face_shapes.GULP_TEETH_RECT_POINTS[0]],
                theme["mouth_stroke"], face_shapes.GULP_TEETH_STROKE_WIDTH,
            )
            self._draw_thick_open_path(
                face_shapes.GULP_OUTLINE_POINTS + [face_shapes.GULP_OUTLINE_POINTS[0]],
                theme["mouth_stroke"], face_shapes.GULP_OUTLINE_STROKE_WIDTH,
            )

    def _draw(self):
        theme = self._theme
        canvas_w, canvas_h = face_shapes.CANVAS_SIZE

        self._canvas.fill(theme["background"])
        self._draw_eyes()
        self._draw_mouth()

        scale = min(self.width / canvas_w, self.height / canvas_h)
        target_size = (max(1, round(canvas_w * scale)), max(1, round(canvas_h * scale)))
        scaled = pygame.transform.smoothscale(self._canvas, target_size)

        offset_x = (self.width - target_size[0]) / 2
        offset_y = (self.height - target_size[1]) / 2 + self._bob_offset(scale)

        self.screen.fill(theme["background"])
        self.screen.blit(scaled, (offset_x, offset_y))
        pygame.display.flip()

    def tick(self):
        """Advance one frame: handle window events, update animation
        state, redraw. Returns False when the window should close, so
        this can be wired into a bigger loop that owns its own exit
        conditions instead of this module owning the whole program."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_d:
                    self.toggle_theme()
            if event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

        self._update_blink()
        self._update_theme()
        self._draw()
        self.clock.tick(FRAME_RATE)
        return True

    def run(self):
        """Blocking loop for standalone testing. Escape or closing the
        window exits, D toggles light and dark mode."""
        running = True
        while running:
            running = self.tick()
        pygame.quit()


if __name__ == "__main__":
    # Quick manual check: run this file directly to see the face.
    # Cycles moods every few seconds, press D to toggle dark mode,
    # Escape or close the window to quit.
    face = Face(screen_size=(480, 480))
    moods = list(MOOD_EXPRESSIONS.keys())
    mood_index = 0
    next_mood_switch = time.time() + 3

    running = True
    while running:
        if time.time() >= next_mood_switch:
            mood_index = (mood_index + 1) % len(moods)
            face.set_mood(moods[mood_index])
            next_mood_switch = time.time() + 3

        running = face.tick()

    pygame.quit()
