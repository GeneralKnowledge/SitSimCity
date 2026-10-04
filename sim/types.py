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
    AT_CAFE = auto()
    AT_SHOP = auto()
    AT_PUB = auto()
    VISITING = auto()


@dataclass(frozen=True)
class ScheduleEntry:
    """Agenda item: at minute_of_day, pursue this activity at target building."""

    minute_of_day: int
    activity: Activity
    target_building_id: int | None = None


@dataclass(frozen=True)
class Tendencies:
    """Simple 0–100 leanings. Probabilities, not character classes."""

    sociability: int
    homebody: int
    cafe_affinity: int
    shop_affinity: int
    pub_affinity: int
    routine_adherence: int


@dataclass
class Relationship:
    """Persistent pairwise social memory. History events live on Person; this accumulates."""

    a_id: int
    b_id: int
    familiarity: int = 0
    friendship: int = 0
    peak_friendship: int = 0
    times_met: int = 0
    meetings_work: int = 0
    meetings_pub: int = 0
    meetings_cafe: int = 0
    meetings_shop: int = 0
    meetings_visit: int = 0
    meetings_other: int = 0
    first_met_total_minutes: int = -1
    last_met_total_minutes: int = -10_000
    recent_contexts: list[str] = field(default_factory=list)


@dataclass
class Building:
    id: int
    kind: BuildingKind
    name: str
    x: int
    y: int
    street_name: str = ""
    occupation: str = ""
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
    tendencies: Tendencies
    activity: Activity = Activity.SLEEP
    path: list[tuple[int, int]] = field(default_factory=list)
    path_index: int = 0
    move_progress: float = 0.0
    schedule: list[ScheduleEntry] = field(default_factory=list)
    wake_offset_minutes: int = 0
    # Short labels for today's optional plans (for inspect UI / debugging).
    plan_notes: list[str] = field(default_factory=list)
    # Mundane memory: sticky habits + a short discoverable history log.
    history: list[str] = field(default_factory=list)
    habit_evening: str | None = None  # home | pub | shop | cafe | visit
    favorite_visit_id: int | None = None


# Walkable speed in tiles per simulated minute.
WALK_SPEED_TILES_PER_MINUTE = 1.0

# Default real-time mapping: 1 real second -> 10 sim minutes at 1x.
DEFAULT_SIM_MINUTES_PER_REAL_SECOND = 10.0

SPEED_STEPS: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 100.0)

MINUTES_PER_DAY = 1440

# Social: don't bump scores every minute of shared presence.
SOCIAL_COOLDOWN_MINUTES = 60
FAMILIARITY_MAX = 100
FRIENDSHIP_MAX = 100

# Per-meeting deltas by context.
WORK_FAMILIARITY_BUMP = 2
WORK_FRIENDSHIP_BUMP = 0
WORK_FRIENDSHIP_RARE_BUMP = 1
WORK_RARE_SOCIABILITY = 85

AMENITY_FAMILIARITY_BUMP = 2
AMENITY_FRIENDSHIP_BUMP = 3
AMENITY_FRIENDSHIP_HIGH_BUMP = 4
AMENITY_HIGH_SOCIABILITY = 70

VISIT_FAMILIARITY_BUMP = 2
VISIT_FRIENDSHIP_BUMP = 4

OTHER_FAMILIARITY_BUMP = 1
OTHER_FRIENDSHIP_BUMP = 1

# Staleness: after this many full days apart, friendship decays 1/day on day roll.
STALE_AFTER_DAYS = 2
FRIENDSHIP_DECAY_PER_DAY = 1

# Inspector / query thresholds.
CLOSE_FRIENDSHIP_MIN = 20
CLOSE_RECENT_DAYS = 3
ACQUAINTANCE_FAMILIARITY_MIN = 15
ACQUAINTANCE_FRIENDSHIP_MAX = 12
STALE_PEAK_MIN = 20
STALE_DAYS_APART = 3
