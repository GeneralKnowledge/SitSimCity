from __future__ import annotations

from dataclasses import dataclass

from sim.types import (
    DEFAULT_SIM_MINUTES_PER_REAL_SECOND,
    MINUTES_PER_DAY,
    SPEED_STEPS,
)


@dataclass
class Clock:
    day: int = 1
    minute_of_day: int = 6 * 60  # start just before the morning commute
    paused: bool = False
    speed: float = 1.0
    sim_minutes_per_real_second: float = DEFAULT_SIM_MINUTES_PER_REAL_SECOND
    _accumulator: float = 0.0

    @property
    def hour(self) -> int:
        return self.minute_of_day // 60

    @property
    def minute(self) -> int:
        return self.minute_of_day % 60

    def format_time(self) -> str:
        return f"Day {self.day}  {self.hour:02d}:{self.minute:02d}"

    def set_speed(self, speed: float) -> None:
        # Snap to nearest supported step for predictable controls.
        self.speed = min(SPEED_STEPS, key=lambda s: abs(s - speed))

    def cycle_speed(self) -> None:
        idx = SPEED_STEPS.index(self.speed) if self.speed in SPEED_STEPS else 1
        self.speed = SPEED_STEPS[(idx + 1) % len(SPEED_STEPS)]

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def consume_real_time(self, real_dt_seconds: float) -> int:
        """Convert wall-clock dt into whole simulation minutes to advance."""
        if self.paused or real_dt_seconds <= 0:
            return 0
        self._accumulator += (
            real_dt_seconds * self.sim_minutes_per_real_second * self.speed
        )
        steps = int(self._accumulator)
        self._accumulator -= steps
        return steps

    def advance_one_minute(self) -> bool:
        """Advance one sim minute. Returns True when the calendar day rolls."""
        self.minute_of_day += 1
        if self.minute_of_day >= MINUTES_PER_DAY:
            self.minute_of_day = 0
            self.day += 1
            return True
        return False
