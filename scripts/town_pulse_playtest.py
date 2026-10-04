#!/usr/bin/env python3
"""M8: short headless sit — density, shifts, mid-day pulse on seeds 7/1/13."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.types import Activity
from sim.world import create_world

STREET = {
    Activity.TRAVEL,
    Activity.AT_CAFE,
    Activity.AT_SHOP,
    Activity.AT_PUB,
    Activity.VISITING,
}


def snapshot(world, label: str) -> None:
    acts = Counter(p.activity.name for p in world.people.values())
    shifts = Counter(p.shift for p in world.people.values())
    out = sum(1 for p in world.people.values() if p.activity in STREET)
    day_work = sum(
        1 for p in world.people.values() if p.shift == "day" and p.activity == Activity.WORK
    )
    eve_work = sum(
        1
        for p in world.people.values()
        if p.shift == "evening" and p.activity == Activity.WORK
    )
    print(f"\n{label} · day {world.clock.day} {world.clock.hour:02d}:{world.clock.minute:02d}")
    print(f"  shifts: {dict(shifts)}")
    print(f"  day@work={day_work} evening@work={eve_work} street/amenity={out}")
    print(f"  activities: {dict(acts)}")


def sit(seed: int, citizens: int = 80) -> None:
    world = create_world(seed=seed, citizen_count=citizens)
    print("=" * 64)
    print(f"SEED {seed} · {citizens} citizens · buildings={len(world.buildings)}")
    kinds = Counter(b.kind.name for b in world.buildings.values())
    print(f"  town: {dict(kinds)}")
    snapshot(world, "start")
    world.step_minutes(2 * 60)  # 08:00 rush
    snapshot(world, "morning rush ~08:00")
    world.step_minutes(2 * 60 + 30)  # 10:30
    snapshot(world, "mid-morning ~10:30")
    world.step_minutes(2 * 60)  # 12:30 lunch
    snapshot(world, "lunch band ~12:30")
    world.step_minutes(4 * 60 + 45)  # 17:15 evening rush
    snapshot(world, "evening rush ~17:15")
    world.step_minutes(5 * 60 + 45)  # 23:00
    snapshot(world, "late night ~23:00")


def main() -> None:
    for seed in (7, 1, 13):
        sit(seed)


if __name__ == "__main__":
    main()
