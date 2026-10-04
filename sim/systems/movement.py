from __future__ import annotations

from collections.abc import Callable

from sim.pathfinding import find_path
from sim.types import Activity, Person, WALK_SPEED_TILES_PER_MINUTE


def begin_travel(
    person: Person,
    target_xy: tuple[int, int],
    is_walkable: Callable[[int, int], bool],
) -> None:
    start = (int(round(person.x)), int(round(person.y)))
    path = find_path(start, target_xy, is_walkable)
    if not path:
        # Snap if somehow disconnected; keeps the sim resilient.
        person.x = float(target_xy[0])
        person.y = float(target_xy[1])
        person.path = []
        person.path_index = 0
        person.move_progress = 0.0
        return
    person.path = path
    person.path_index = 0
    person.move_progress = 0.0
    person.activity = Activity.TRAVEL
    person.x = float(path[0][0])
    person.y = float(path[0][1])


def advance_movement(person: Person, minutes: float = 1.0) -> bool:
    """Move along path. Returns True when the destination tile is reached."""
    if not person.path:
        return True
    if person.path_index >= len(person.path) - 1:
        goal = person.path[-1]
        person.x = float(goal[0])
        person.y = float(goal[1])
        person.path = []
        person.path_index = 0
        person.move_progress = 0.0
        return True

    remaining = minutes * WALK_SPEED_TILES_PER_MINUTE
    while remaining > 0 and person.path_index < len(person.path) - 1:
        need = 1.0 - person.move_progress
        step = min(remaining, need)
        person.move_progress += step
        remaining -= step
        a = person.path[person.path_index]
        b = person.path[person.path_index + 1]
        t = person.move_progress
        person.x = a[0] + (b[0] - a[0]) * t
        person.y = a[1] + (b[1] - a[1]) * t
        if person.move_progress >= 1.0 - 1e-9:
            person.path_index += 1
            person.move_progress = 0.0
            person.x = float(person.path[person.path_index][0])
            person.y = float(person.path[person.path_index][1])

    if person.path_index >= len(person.path) - 1:
        goal = person.path[-1]
        person.x = float(goal[0])
        person.y = float(goal[1])
        person.path = []
        person.path_index = 0
        person.move_progress = 0.0
        return True
    return False
