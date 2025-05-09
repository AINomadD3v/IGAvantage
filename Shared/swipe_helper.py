import logging
import math
import random
import time

logger = logging.getLogger("Scroller")


class SwipeHelper:
    def __init__(self, device):
        self.device = device

    def _curved_path(
        self, start, end, steps=20, max_arc_x=30, jitter_y=3, intensity="medium"
    ):
        x1, y1 = start
        x2, y2 = end
        path = []

        # Apply intensity presets
        if intensity == "gentle":
            max_arc_x = 10
            jitter_y = 1
        elif intensity == "chaotic":
            max_arc_x = 50
            jitter_y = 6
        # "medium" is default

        for i in range(steps + 1):
            t = i / steps
            arc_offset = math.sin(t * math.pi) * random.uniform(-max_arc_x, max_arc_x)
            jitter = random.uniform(-jitter_y, jitter_y)
            x = x1 + (x2 - x1) * t + arc_offset
            y = y1 + (y2 - y1) * t + jitter
            path.append((int(x), int(y)))

        return path

    def _perform_path_swipe(self, path, total_duration_ms):
        interval = total_duration_ms / len(path)
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            dur = int(interval)
            self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {dur}")
            time.sleep(interval / 1000.0)

    def curved_swipe(self, start, end, duration=400, intensity="medium"):
        logger.info(
            f"🌀 Executing curved swipe: {start} → {end} over {duration}ms (style: {intensity})"
        )
        path = self._curved_path(start, end, steps=20, intensity=intensity)
        self._perform_path_swipe(path, total_duration_ms=duration)

    def curved_tap(self, target_x, target_y, arc_radius=80, steps=10):
        """Simulate a curved tap motion ending at (target_x, target_y)."""
        start_x = target_x - random.randint(arc_radius // 2, arc_radius)
        start_y = target_y + random.randint(arc_radius // 2, arc_radius)

        logger.info(
            f"👆 Curved tap from ({start_x}, {start_y}) to ({target_x}, {target_y})"
        )

        path = self._curved_path(
            start=(start_x, start_y),
            end=(target_x, target_y),
            steps=steps,
            max_arc_x=15,
            jitter_y=2,
            intensity="gentle",
        )
        self._perform_path_swipe(path, total_duration_ms=100 + random.randint(50, 120))

    def human_scroll_up(self):
        """Scroll up in a controlled human-like way (downward swipe)."""
        x = random.randint(500, 580)
        y_start = random.randint(1200, 1400)
        y_end = random.randint(600, 800)  # Must be LESS than y_start to swipe downward
        dur = random.randint(300, 600)
        intensity = random.choice(["gentle", "medium"])

        # Ensure swipe goes downward on screen
        if y_start <= y_end:
            y_start, y_end = y_end + 200, y_end  # force downward movement

        self.curved_swipe(
            start=(x, y_start), end=(x, y_end), duration=dur, intensity=intensity
        )

    def human_scroll_down(self):
        """Scroll down (reverse) in a human-like way."""
        x = random.randint(500, 580)
        y_start = random.randint(600, 800)
        y_end = random.randint(1200, 1400)
        dur = random.randint(300, 600)
        intensity = random.choice(["gentle", "medium", "chaotic"])

        self.curved_swipe(
            start=(x, y_start), end=(x, y_end), duration=dur, intensity=intensity
        )

    def human_like_scroll(self):
        """Human-like scrolls, constrained to proper downward direction."""
        mode = random.choice(["standard", "jitter"])
        logger.info(f"↕️ Human scroll mode: {mode}")

        if mode == "standard":
            self.human_scroll_up()

        elif mode == "jitter":
            self.human_scroll_up()
            time.sleep(random.uniform(0.1, 0.3))
            self.human_scroll_up()
