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
    # True once friendship has ever crossed the close threshold (M6 inspector).
    ever_close: bool = False
    # Day of last recorded reunion event (-1 = never); throttles REUNITED spam.
    last_reunion_day: int = -1
    # Short deterministic notes about life changes that affected this bond.
    story_notes: list[str] = field(default_factory=list)


class CircumstanceKind(Enum):
    SICK = auto()
    UNEMPLOYED = auto()
    OVERWORKED = auto()
    RECENTLY_MOVED = auto()


@dataclass
class Circumstance:
    """Temporary state that reshapes opportunity, not friendship math."""

    kind: CircumstanceKind
    start_day: int
    end_day: int  # inclusive; removed when clock.day > end_day
    note: str = ""


class LifeEventKind(Enum):
    BECAME_SICK = auto()
    RECOVERED = auto()
    BECAME_UNEMPLOYED = auto()
    JOB_CHANGED = auto()
    MOVED_HOME = auto()
    BECAME_OVERWORKED = auto()
    OVERWORK_ENDED = auto()
    BECAME_CLOSE = auto()
    REUNITED = auto()


@dataclass(frozen=True)
class LifeEvent:
    kind: LifeEventKind
    day: int
    detail: str
    related_person_id: int | None = None


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
    # M6: temporary circumstances + typed life-change log.
    circumstances: list[Circumstance] = field(default_factory=list)
    life_events: list[LifeEvent] = field(default_factory=list)


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

# Familiarity bumps (broad recognition).
WORK_FAMILIARITY_BUMP = 2
AMENITY_FAMILIARITY_BUMP = 2
VISIT_FAMILIARITY_BUMP = 2
OTHER_FAMILIARITY_BUMP = 1

# Work never grants friendship (M5.5: know coworkers without being close).
WORK_FRIENDSHIP_BUMP = 0

# Amenity / visit friendship bases before diminishing returns.
AMENITY_PUB_FRIENDSHIP_BASE = 3
AMENITY_CAFE_SHOP_FRIENDSHIP_BASE = 2
AMENITY_HIGH_SOCIABILITY = 70
AMENITY_HIGH_SOCIABILITY_BONUS = 1
VISIT_FRIENDSHIP_BASE = 4

# Diminishing-return k: gain ≈ base / sqrt(1 + friendship / k)
FRIENDSHIP_K_EARLY = 18
FRIENDSHIP_K_LATE = 10
FRIENDSHIP_K_VISIT = 25

# After this friendship, ordinary amenity meetings drip rarely.
FRIENDSHIP_DRIP_THRESHOLD = 60
FRIENDSHIP_DRIP_EVERY_N_SOCIAL = 4

# Staleness / reactivation.
STALE_AFTER_DAYS = 2
FRIENDSHIP_DECAY_PER_DAY = 1
FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS = 4
FRIENDSHIP_DECAY_EVER_CLOSE_PER_DAY = 2
REACTIVATION_COOL_FRACTION = 0.6
REACTIVATION_MIN_DAYS_APART = 2
REACTIVATION_AMENITY_BUMP = 1
REACTIVATION_VISIT_BUMP = 2

# Inspector / query thresholds.
CLOSE_FRIENDSHIP_MIN = 20
CLOSE_RECENT_DAYS = 3
ACQUAINTANCE_FAMILIARITY_MIN = 15
ACQUAINTANCE_FRIENDSHIP_MAX = 12
STALE_PEAK_MIN = 20
STALE_DAYS_APART = 3
COOLING_LAST_SEEN_DAYS = 3

# --- M6 circumstances (opportunity effects only; do not retune friendship math) ---
SICK_DAILY_CHANCE = 0.012
SICK_MIN_DAYS = 2
SICK_MAX_DAYS = 5

UNEMPLOYED_DAILY_CHANCE = 0.003
UNEMPLOYED_MIN_DAYS = 3
UNEMPLOYED_MAX_DAYS = 7

OVERWORKED_DAILY_CHANCE = 0.008
OVERWORKED_MIN_DAYS = 2
OVERWORKED_MAX_DAYS = 4

MOVE_DAILY_CHANCE = 0.0025
RECENTLY_MOVED_DAYS = 5

LIFE_EVENT_HISTORY_LIMIT = 24
CIRCUMSTANCE_NOTE_LIMIT = 4
