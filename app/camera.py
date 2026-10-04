from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Camera:
    x: float = 0.0  # world pixels top-left
    y: float = 0.0
    zoom: float = 1.0
    min_zoom: float = 0.5
    max_zoom: float = 3.0

    def pan(self, dx: float, dy: float) -> None:
        self.x += dx / self.zoom
        self.y += dy / self.zoom

    def adjust_zoom(self, factor: float, anchor_screen: tuple[int, int]) -> None:
        old = self.zoom
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        if self.zoom == old:
            return
        ax, ay = anchor_screen
        # Keep the world point under the cursor stable.
        world_x = self.x + ax / old
        world_y = self.y + ay / old
        self.x = world_x - ax / self.zoom
        self.y = world_y - ay / self.zoom

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return self.x + sx / self.zoom, self.y + sy / self.zoom

    def center_on(self, wx: float, wy: float, screen_w: int, screen_h: int) -> None:
        self.x = wx - (screen_w / 2) / self.zoom
        self.y = wy - (screen_h / 2) / self.zoom
