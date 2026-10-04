from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class TileKind(Enum):
    EMPTY = auto()
    ROAD = auto()
    BUILDING = auto()


class BuildingKind(Enum):
    HOME = auto()
    WORKPLACE = auto()
    PUB = auto()
    SHOP = auto()
    CAFE = auto()
    POLICE = auto()
    HOSPITAL = auto()


class Activity(Enum):
    SLEEP = auto()
    AT_HOME = auto()
    TRAVEL = auto()
    WORK = auto()
    WAIT = auto()


@dataclass(frozen=True)
class ScheduleEntry:
    """Agenda item: at minute_of_day, begin this activity toward target building."""

    minute_of_day: int
    activity: Activity
    target_building_id: int | None = None


@dataclass
class Building:
    id: int
    kind: BuildingKind
    name: str
    x: int
    y: int
    street_name: str = ""
    occupation: str = ""  # for workplaces: default job title
    capacity: int = 8


@dataclass
class Person:
    id: int
    name: str
    age: int
    home_id: int
    work_id: int
    occupation: str
    x: float
    y: float
    activity: Activity = Activity.SLEEP
    path: list[tuple[int, int]] = field(default_factory=list)
    path_index: int = 0
    move_progress: float = 0.0
    schedule: list[ScheduleEntry] = field(default_factory=list)
    # Personal offset so the morning rush is staggered, not a single teleport.
    wake_offset_minutes: int = 0


# Walkable speed in tiles per simulated minute.
# Sized so typical home→work walks take roughly 20–40 sim minutes.
WALK_SPEED_TILES_PER_MINUTE = 1.0

# Default real-time mapping: 1 real second -> 10 sim minutes at 1x.
DEFAULT_SIM_MINUTES_PER_REAL_SECOND = 10.0

SPEED_STEPS: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 100.0)

MINUTES_PER_DAY = 1440
