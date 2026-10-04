from __future__ import annotations

import random

from sim.generate import names
from sim.generate.city import CityLayout
from sim.generate.tendencies import roll_tendencies
from sim.types import Activity, BuildingKind, Person


def populate_city(
    rng: random.Random,
    layout: CityLayout,
    citizen_count: int = 80,
) -> dict[int, Person]:
    homes = [b for b in layout.buildings.values() if b.kind == BuildingKind.HOME]
    workplaces = [b for b in layout.buildings.values() if b.kind == BuildingKind.WORKPLACE]
    if not homes or not workplaces:
        raise ValueError("City needs homes and workplaces before population")

    used_names: set[str] = set()
    people: dict[int, Person] = {}
    home_loads = {h.id: 0 for h in homes}
    work_loads = {w.id: 0 for w in workplaces}

    for i in range(citizen_count):
        home = _pick_with_capacity(rng, homes, home_loads)
        work = _pick_with_capacity(rng, workplaces, work_loads)
        home_loads[home.id] += 1
        work_loads[work.id] += 1
        person_id = i + 1
        # ~75% day / ~25% evening — evening shifters keep mid-day streets alive.
        shift = "evening" if rng.random() < 0.25 else "day"
        people[person_id] = Person(
            id=person_id,
            name=names.person_name(rng, used_names),
            age=rng.randint(22, 64),
            home_id=home.id,
            work_id=work.id,
            occupation=work.occupation or rng.choice(names.OCCUPATIONS),
            x=float(home.x),
            y=float(home.y),
            tendencies=roll_tendencies(rng),
            activity=Activity.SLEEP,
            wake_offset_minutes=rng.randint(0, 60),
            shift=shift,
        )
    return people


def _pick_with_capacity(rng: random.Random, buildings, loads: dict[int, int]):
    candidates = [b for b in buildings if loads[b.id] < b.capacity]
    if not candidates:
        candidates = list(buildings)
    candidates.sort(key=lambda b: (loads[b.id], b.id))
    top = candidates[: max(1, len(candidates) // 3)]
    return rng.choice(top)
