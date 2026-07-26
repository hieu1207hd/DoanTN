import time


class FPSCounter:
    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self._last_time = None
        self.fps = 0.0

    def update(self):
        now = time.time()
        if self._last_time is not None:
            dt = now - self._last_time
            if dt > 0:
                instant_fps = 1.0 / dt
                self.fps = self.alpha * instant_fps + (1 - self.alpha) * self.fps
        self._last_time = now
        return self.fps
