from __future__ import annotations

import heapq
from collections.abc import Callable


def find_path(
    start: tuple[int, int],
    goal: tuple[int, int],
    is_walkable: Callable[[int, int], bool],
) -> list[tuple[int, int]]:
    """A* on a 4-connected grid. Returns tile list including start and goal."""
    if start == goal:
        return [start]
    if not is_walkable(*goal):
        return []

    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_heap: list[tuple[int, int, tuple[int, int]]] = []
    heapq.heappush(open_heap, (0, 0, start))
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    g_score: dict[tuple[int, int], int] = {start: 0}
    counter = 1

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            return _reconstruct(came_from, current)

        cx, cy = current
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if not is_walkable(nx, ny):
                continue
            tentative = g_score[current] + 1
            neighbor = (nx, ny)
            if tentative >= g_score.get(neighbor, 1_000_000):
                continue
            came_from[neighbor] = current
            g_score[neighbor] = tentative
            f = tentative + heuristic(neighbor, goal)
            heapq.heappush(open_heap, (f, counter, neighbor))
            counter += 1

    return []


def _reconstruct(
    came_from: dict[tuple[int, int], tuple[int, int] | None],
    current: tuple[int, int],
) -> list[tuple[int, int]]:
    path = [current]
    while came_from[current] is not None:
        current = came_from[current]  # type: ignore[assignment]
        path.append(current)
    path.reverse()
    return path
