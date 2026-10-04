from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sim.types import (
    ACQUAINTANCE_FAMILIARITY_MIN,
    ACQUAINTANCE_FRIENDSHIP_MAX,
    AMENITY_FAMILIARITY_BUMP,
    AMENITY_FRIENDSHIP_BUMP,
    AMENITY_FRIENDSHIP_HIGH_BUMP,
    AMENITY_HIGH_SOCIABILITY,
    CLOSE_FRIENDSHIP_MIN,
    CLOSE_RECENT_DAYS,
    FAMILIARITY_MAX,
    FRIENDSHIP_DECAY_PER_DAY,
    FRIENDSHIP_MAX,
    MINUTES_PER_DAY,
    OTHER_FAMILIARITY_BUMP,
    OTHER_FRIENDSHIP_BUMP,
    SOCIAL_COOLDOWN_MINUTES,
    STALE_AFTER_DAYS,
    STALE_DAYS_APART,
    STALE_PEAK_MIN,
    VISIT_FAMILIARITY_BUMP,
    VISIT_FRIENDSHIP_BUMP,
    WORK_FAMILIARITY_BUMP,
    WORK_FRIENDSHIP_BUMP,
    WORK_FRIENDSHIP_RARE_BUMP,
    WORK_RARE_SOCIABILITY,
    Activity,
    Relationship,
)

if TYPE_CHECKING:
    from sim.world import World

AMENITY_ACTIVITIES = {
    Activity.AT_PUB,
    Activity.AT_CAFE,
    Activity.AT_SHOP,
    Activity.VISITING,
}

# Preferred social ranking when two people are in different amenity activities.
_CONTEXT_PRIORITY = {
    "visit": 5,
    "pub": 4,
    "cafe": 3,
    "shop": 2,
    "work": 1,
    "other": 0,
}


def relationship_key(a_id: int, b_id: int) -> tuple[int, int]:
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def get_relationship(world: World, a_id: int, b_id: int) -> Relationship:
    key = relationship_key(a_id, b_id)
    rel = world.relationships.get(key)
    if rel is None:
        rel = Relationship(a_id=key[0], b_id=key[1])
        world.relationships[key] = rel
    return rel


def social_meeting_count(rel: Relationship) -> int:
    return (
        rel.meetings_pub
        + rel.meetings_cafe
        + rel.meetings_shop
        + rel.meetings_visit
    )


def process_colocations(world: World) -> None:
    """If citizens share a non-travel tile, record a sparse meeting and update memory."""
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


def apply_relationship_staleness(world: World) -> None:
    """Decay friendship for pairs who have not met recently. Preserve totals and peak."""
    now = world.total_minutes()
    for rel in world.relationships.values():
        if rel.times_met <= 0 or rel.first_met_total_minutes < 0:
            continue
        days_since = (now - rel.last_met_total_minutes) // MINUTES_PER_DAY
        if days_since >= STALE_AFTER_DAYS:
            rel.friendship = max(0, rel.friendship - FRIENDSHIP_DECAY_PER_DAY)


def _maybe_meet(world: World, a_id: int, b_id: int, total_minutes: int) -> None:
    rel = get_relationship(world, a_id, b_id)
    if total_minutes - rel.last_met_total_minutes < SOCIAL_COOLDOWN_MINUTES:
        return

    a = world.people[a_id]
    b = world.people[b_id]
    context = _classify_context(a.activity, b.activity)
    fam_bump, friend_bump = _score_bumps(context, a.tendencies.sociability, b.tendencies.sociability)

    rel.times_met += 1
    _increment_context_counter(rel, context)
    if rel.first_met_total_minutes < 0:
        rel.first_met_total_minutes = total_minutes
    rel.last_met_total_minutes = total_minutes

    rel.familiarity = min(FAMILIARITY_MAX, rel.familiarity + fam_bump)
    rel.friendship = min(FRIENDSHIP_MAX, rel.friendship + friend_bump)
    rel.peak_friendship = max(rel.peak_friendship, rel.friendship)

    if context != "work":
        _append_recent_context(rel, context)
        if context in {"pub", "cafe", "shop", "visit"}:
            place = _place_label(context)
            _append_history(a, f"Saw {b.name} at {place}")
            _append_history(b, f"Saw {a.name} at {place}")


def _classify_context(a_activity: Activity, b_activity: Activity) -> str:
    if a_activity == Activity.WORK and b_activity == Activity.WORK:
        return "work"

    a_ctx = _activity_context(a_activity)
    b_ctx = _activity_context(b_activity)
    if a_ctx in AMENITY_CONTEXT_NAMES and b_ctx in AMENITY_CONTEXT_NAMES:
        if a_ctx == b_ctx:
            return a_ctx
        # Prefer the more socially meaningful shared reading.
        if _CONTEXT_PRIORITY[a_ctx] >= _CONTEXT_PRIORITY[b_ctx]:
            return a_ctx
        return b_ctx
    if a_ctx in AMENITY_CONTEXT_NAMES:
        return a_ctx
    if b_ctx in AMENITY_CONTEXT_NAMES:
        return b_ctx
    return "other"


AMENITY_CONTEXT_NAMES = frozenset({"pub", "cafe", "shop", "visit"})


def _activity_context(activity: Activity) -> str:
    if activity == Activity.WORK:
        return "work"
    if activity == Activity.AT_PUB:
        return "pub"
    if activity == Activity.AT_CAFE:
        return "cafe"
    if activity == Activity.AT_SHOP:
        return "shop"
    if activity == Activity.VISITING:
        return "visit"
    return "other"


def _score_bumps(context: str, soc_a: int, soc_b: int) -> tuple[int, int]:
    if context == "work":
        friend = WORK_FRIENDSHIP_BUMP
        if soc_a >= WORK_RARE_SOCIABILITY and soc_b >= WORK_RARE_SOCIABILITY:
            friend = WORK_FRIENDSHIP_RARE_BUMP
        return WORK_FAMILIARITY_BUMP, friend
    if context == "visit":
        return VISIT_FAMILIARITY_BUMP, VISIT_FRIENDSHIP_BUMP
    if context in {"pub", "cafe", "shop"}:
        friend = AMENITY_FRIENDSHIP_BUMP
        if soc_a >= AMENITY_HIGH_SOCIABILITY and soc_b >= AMENITY_HIGH_SOCIABILITY:
            friend = AMENITY_FRIENDSHIP_HIGH_BUMP
        return AMENITY_FAMILIARITY_BUMP, friend
    return OTHER_FAMILIARITY_BUMP, OTHER_FRIENDSHIP_BUMP


def _increment_context_counter(rel: Relationship, context: str) -> None:
    if context == "work":
        rel.meetings_work += 1
    elif context == "pub":
        rel.meetings_pub += 1
    elif context == "cafe":
        rel.meetings_cafe += 1
    elif context == "shop":
        rel.meetings_shop += 1
    elif context == "visit":
        rel.meetings_visit += 1
    else:
        rel.meetings_other += 1


def _append_recent_context(rel: Relationship, context: str) -> None:
    rel.recent_contexts.append(context)
    if len(rel.recent_contexts) > 4:
        rel.recent_contexts = rel.recent_contexts[-4:]


def _place_label(context: str) -> str:
    if context == "pub":
        return "the pub"
    if context == "cafe":
        return "the cafe"
    if context == "shop":
        return "the shop"
    if context == "visit":
        return "a visit"
    return "town"


def _append_history(person, line: str) -> None:
    if person.history and person.history[-1] == line:
        return
    person.history.append(line)
    if len(person.history) > 12:
        person.history = person.history[-12:]


def record_arrival(person, activity: Activity, place_name: str) -> None:
    """Log a mundane arrival so follow/inspect can show a life unfolding."""
    if activity == Activity.AT_PUB:
        _append_history(person, f"Went to {place_name}")
    elif activity == Activity.AT_CAFE:
        _append_history(person, f"Stopped at {place_name}")
    elif activity == Activity.AT_SHOP:
        _append_history(person, f"Shopped at {place_name}")
    elif activity == Activity.VISITING:
        _append_history(person, f"Visited {place_name}")


def dominant_meeting_place(rel: Relationship) -> str | None:
    """Return a short place word for the strongest non-work meeting context."""
    options = [
        (rel.meetings_visit, "visits"),
        (rel.meetings_pub, "pub"),
        (rel.meetings_cafe, "cafe"),
        (rel.meetings_shop, "shop"),
    ]
    options.sort(reverse=True)
    count, label = options[0]
    if count <= 0:
        return None
    return label


def _iter_person_relationships(world: World, person_id: int):
    for (a, b), rel in world.relationships.items():
        if a == person_id:
            yield b, rel
        elif b == person_id:
            yield a, rel


def close_companions(
    world: World, person_id: int, limit: int = 3
) -> list[tuple[int, Relationship, str]]:
    """People with genuine recent friendship, plus a place label."""
    now = world.total_minutes()
    recent_cutoff = CLOSE_RECENT_DAYS * MINUTES_PER_DAY
    scored: list[tuple[int, int, int, Relationship, str]] = []
    for other_id, rel in _iter_person_relationships(world, person_id):
        if rel.friendship < CLOSE_FRIENDSHIP_MIN:
            continue
        if now - rel.last_met_total_minutes > recent_cutoff:
            continue
        place = dominant_meeting_place(rel) or "town"
        scored.append((rel.friendship, social_meeting_count(rel), other_id, rel, place))
    scored.sort(reverse=True)
    return [(other_id, rel, place) for _, _, other_id, rel, place in scored[:limit]]


def work_acquaintances(
    world: World, person_id: int, limit: int = 3
) -> list[tuple[int, Relationship]]:
    """Coworkers known mainly through work, not close friendship."""
    person = world.people[person_id]
    scored: list[tuple[int, int, int, Relationship]] = []
    for other_id, rel in _iter_person_relationships(world, person_id):
        other = world.people[other_id]
        if other.work_id != person.work_id:
            continue
        if rel.familiarity < ACQUAINTANCE_FAMILIARITY_MIN:
            continue
        if rel.friendship > ACQUAINTANCE_FRIENDSHIP_MAX:
            continue
        scored.append((rel.familiarity, rel.meetings_work, other_id, rel))
    scored.sort(reverse=True)
    return [(other_id, rel) for _, _, other_id, rel in scored[:limit]]


def stale_companions(
    world: World, person_id: int, limit: int = 1
) -> list[tuple[int, Relationship]]:
    """People who used to be close but have drifted."""
    now = world.total_minutes()
    scored: list[tuple[int, int, int, Relationship]] = []
    for other_id, rel in _iter_person_relationships(world, person_id):
        if rel.peak_friendship < STALE_PEAK_MIN:
            continue
        days_apart = (now - rel.last_met_total_minutes) // MINUTES_PER_DAY
        faded = rel.friendship <= rel.peak_friendship // 2
        distant = days_apart >= STALE_DAYS_APART
        if not (faded or distant):
            continue
        scored.append((rel.peak_friendship, -rel.friendship, other_id, rel))
    scored.sort(reverse=True)
    return [(other_id, rel) for _, _, other_id, rel in scored[:limit]]


def recurring_social(
    world: World, person_id: int, limit: int = 1
) -> list[tuple[int, Relationship, str]]:
    """Someone often seen socially who may not yet clear the close-friend bar."""
    close_ids = {other_id for other_id, _, _ in close_companions(world, person_id, limit=8)}
    scored: list[tuple[int, int, int, Relationship, str]] = []
    for other_id, rel in _iter_person_relationships(world, person_id):
        if other_id in close_ids:
            continue
        social = social_meeting_count(rel)
        if social < 3:
            continue
        place = dominant_meeting_place(rel)
        if place is None:
            continue
        scored.append((social, rel.friendship, other_id, rel, place))
    scored.sort(reverse=True)
    return [(other_id, rel, place) for _, _, other_id, rel, place in scored[:limit]]


def social_summary_lines(world: World, person_id: int) -> list[str]:
    """Short prose lines for the observer inspector."""
    lines: list[str] = []

    close = close_companions(world, person_id, limit=3)
    if close:
        parts = []
        for other_id, _rel, place in close:
            parts.append(f"{world.people[other_id].name} ({place})")
        lines.append("Close with: " + ", ".join(parts))

    recurring = recurring_social(world, person_id, limit=1)
    if recurring:
        other_id, _rel, place = recurring[0]
        place_phrase = f"at the {place}" if place != "visits" else "on visits"
        lines.append(f"Often sees: {world.people[other_id].name} {place_phrase}")

    work = work_acquaintances(world, person_id, limit=3)
    if work:
        names = ", ".join(world.people[oid].name for oid, _ in work)
        lines.append(f"At work knows: {names}")

    stale = stale_companions(world, person_id, limit=1)
    if stale:
        other_id, _rel = stale[0]
        lines.append(f"Used to see: {world.people[other_id].name}")

    return lines
