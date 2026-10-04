from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sim.types import (
    FRIENDSHIP_MAX,
    SOCIAL_COOLDOWN_MINUTES,
    Activity,
    Relationship,
)

if TYPE_CHECKING:
    from sim.world import World


def relationship_key(a_id: int, b_id: int) -> tuple[int, int]:
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def get_relationship(world: World, a_id: int, b_id: int) -> Relationship:
    key = relationship_key(a_id, b_id)
    rel = world.relationships.get(key)
    if rel is None:
        rel = Relationship(a_id=key[0], b_id=key[1])
        world.relationships[key] = rel
    return rel


def process_colocations(world: World) -> None:
    """If citizens share a non-travel tile, record a sparse meeting and nudge friendship."""
    by_tile: dict[tuple[int, int], list[int]] = defaultdict(list)
    for person in world.people.values():
        if person.activity in (Activity.TRAVEL, Activity.SLEEP):
            continue
        tile = (int(round(person.x)), int(round(person.y)))
        by_tile[tile].append(person.id)

    total_minutes = world.total_minutes()
    for ids in by_tile.values():
        if len(ids) < 2:
            continue
        ids.sort()
        for i, a_id in enumerate(ids):
            for b_id in ids[i + 1 :]:
                _maybe_meet(world, a_id, b_id, total_minutes)


def _maybe_meet(world: World, a_id: int, b_id: int, total_minutes: int) -> None:
    rel = get_relationship(world, a_id, b_id)
    if total_minutes - rel.last_met_total_minutes < SOCIAL_COOLDOWN_MINUTES:
        return

    a = world.people[a_id]
    b = world.people[b_id]
    # Tiny bumps: offices create many meetings, so keep growth slow.
    bump = 1
    if a.tendencies.sociability >= 80 and b.tendencies.sociability >= 80:
        bump = 2

    rel.friendship = min(FRIENDSHIP_MAX, rel.friendship + bump)
    rel.times_met += 1
    rel.last_met_total_minutes = total_minutes

    _remember_meeting(a, b.name)
    _remember_meeting(b, a.name)


def _remember_meeting(person, other_name: str) -> None:
    note = f"Met {other_name}"
    person.recent_meetings.append(note)
    if len(person.recent_meetings) > 8:
        person.recent_meetings = person.recent_meetings[-8:]


def top_friends(world: World, person_id: int, limit: int = 3) -> list[tuple[str, int, int]]:
    """Return (name, friendship, times_met) for strongest relationships."""
    scored: list[tuple[int, int, int]] = []
    for (a, b), rel in world.relationships.items():
        if rel.friendship <= 0 and rel.times_met <= 0:
            continue
        if a == person_id:
            other = b
        elif b == person_id:
            other = a
        else:
            continue
        scored.append((rel.friendship, rel.times_met, other))
    scored.sort(reverse=True)
    result: list[tuple[str, int, int]] = []
    for friendship, times_met, other_id in scored[:limit]:
        result.append((world.people[other_id].name, friendship, times_met))
    return result
