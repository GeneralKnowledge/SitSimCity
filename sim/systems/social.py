from __future__ import annotations

import math
from collections import defaultdict
from typing import TYPE_CHECKING

from sim.types import (
    ACQUAINTANCE_FAMILIARITY_MIN,
    ACQUAINTANCE_FRIENDSHIP_MAX,
    AMENITY_CAFE_SHOP_FRIENDSHIP_BASE,
    AMENITY_FAMILIARITY_BUMP,
    AMENITY_HIGH_SOCIABILITY,
    AMENITY_HIGH_SOCIABILITY_BONUS,
    AMENITY_PUB_FRIENDSHIP_BASE,
    BOND_EVENT_LIMIT,
    CLOSE_FRIENDSHIP_MIN,
    CLOSE_RECENT_DAYS,
    COOLING_LAST_SEEN_DAYS,
    FAMILIARITY_MAX,
    FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS,
    FRIENDSHIP_DECAY_EVER_CLOSE_PER_DAY,
    FRIENDSHIP_DECAY_PER_DAY,
    FRIENDSHIP_DRIP_EVERY_N_SOCIAL,
    FRIENDSHIP_DRIP_THRESHOLD,
    FRIENDSHIP_K_EARLY,
    FRIENDSHIP_K_LATE,
    FRIENDSHIP_K_VISIT,
    FRIENDSHIP_MAX,
    MINUTES_PER_DAY,
    OTHER_FAMILIARITY_BUMP,
    REACTIVATION_AMENITY_BUMP,
    REACTIVATION_COOL_FRACTION,
    REACTIVATION_MIN_DAYS_APART,
    REACTIVATION_VISIT_BUMP,
    SOCIAL_COOLDOWN_MINUTES,
    STALE_AFTER_DAYS,
    STALE_DAYS_APART,
    STALE_PEAK_MIN,
    VISIT_FAMILIARITY_BUMP,
    VISIT_FRIENDSHIP_BASE,
    WORK_FAMILIARITY_BUMP,
    WORK_FRIENDSHIP_BUMP,
    Activity,
    BondEvent,
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

AMENITY_CONTEXT_NAMES = frozenset({"pub", "cafe", "shop", "visit"})


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
    """Decay current friendship when pairs stop meeting. Preserve totals and peak."""
    now = world.total_minutes()
    day = world.clock.day
    for rel in world.relationships.values():
        if rel.times_met <= 0 or rel.first_met_total_minutes < 0:
            continue
        days_since = (now - rel.last_met_total_minutes) // MINUTES_PER_DAY
        if days_since < STALE_AFTER_DAYS:
            continue
        if (
            rel.peak_friendship >= CLOSE_FRIENDSHIP_MIN
            and days_since >= FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS
        ):
            decay = FRIENDSHIP_DECAY_EVER_CLOSE_PER_DAY
        else:
            decay = FRIENDSHIP_DECAY_PER_DAY
        prev = rel.friendship
        rel.friendship = max(0, rel.friendship - decay)
        # Observability only: note first cooling of an ever-close bond.
        if (
            rel.ever_close
            and not rel.cooling_noted
            and rel.friendship < prev
            and rel.friendship < rel.peak_friendship * REACTIVATION_COOL_FRACTION
        ):
            rel.cooling_noted = True
            append_bond_event(
                rel,
                BondEvent(day, "cooling", "Friendship began cooling", None),
            )


def _maybe_meet(world: World, a_id: int, b_id: int, total_minutes: int) -> None:
    rel = get_relationship(world, a_id, b_id)
    if total_minutes - rel.last_met_total_minutes < SOCIAL_COOLDOWN_MINUTES:
        return

    a = world.people[a_id]
    b = world.people[b_id]
    context = _classify_context(a.activity, b.activity)
    days_apart = (total_minutes - rel.last_met_total_minutes) // MINUTES_PER_DAY
    fam_bump, friend_bump = _score_bumps(
        context,
        a.tendencies.sociability,
        b.tendencies.sociability,
        rel,
    )
    friend_bump = _apply_reactivation(rel, context, friend_bump, days_apart)

    is_first_meeting = rel.first_met_total_minutes < 0
    rel.times_met += 1
    _increment_context_counter(rel, context)
    if is_first_meeting:
        rel.first_met_total_minutes = total_minutes
        rel.origin_context = context
        append_bond_event(
            rel,
            BondEvent(
                world.clock.day,
                "first_met",
                f"First met {_origin_phrase(context)}",
                context,
            ),
        )
    rel.last_met_total_minutes = total_minutes

    was_cooled = _is_cooled(rel)
    prev_friendship = rel.friendship
    rel.familiarity = min(FAMILIARITY_MAX, rel.familiarity + fam_bump)
    rel.friendship = min(FRIENDSHIP_MAX, rel.friendship + friend_bump)
    rel.peak_friendship = max(rel.peak_friendship, rel.friendship)

    _record_social_life_events(
        world,
        a,
        b,
        rel,
        prev_friendship=prev_friendship,
        was_cooled=was_cooled,
        days_apart=days_apart,
        friend_bump=friend_bump,
        context=context,
    )

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
        if _CONTEXT_PRIORITY[a_ctx] >= _CONTEXT_PRIORITY[b_ctx]:
            return a_ctx
        return b_ctx
    if a_ctx in AMENITY_CONTEXT_NAMES:
        return a_ctx
    if b_ctx in AMENITY_CONTEXT_NAMES:
        return b_ctx
    return "other"


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


def _diminish(base: int, friendship: int, k: float) -> int:
    """gain ≈ base / sqrt(1 + friendship / k), floored at 0."""
    if base <= 0:
        return 0
    return max(0, int(round(base / math.sqrt(1.0 + friendship / k))))


def _score_bumps(
    context: str,
    soc_a: int,
    soc_b: int,
    rel: Relationship,
) -> tuple[int, int]:
    """Return (familiarity_bump, friendship_bump) with diminishing friendship gains."""
    if context == "work":
        return WORK_FAMILIARITY_BUMP, WORK_FRIENDSHIP_BUMP
    if context == "other":
        return OTHER_FAMILIARITY_BUMP, 0
    if context == "visit":
        gain = _diminish(VISIT_FRIENDSHIP_BASE, rel.friendship, FRIENDSHIP_K_VISIT)
        return VISIT_FAMILIARITY_BUMP, max(1, gain) if rel.friendship < FRIENDSHIP_MAX else 0

    # Amenity: pub / cafe / shop
    if context == "pub":
        base = AMENITY_PUB_FRIENDSHIP_BASE
    else:
        base = AMENITY_CAFE_SHOP_FRIENDSHIP_BASE
    if soc_a >= AMENITY_HIGH_SOCIABILITY and soc_b >= AMENITY_HIGH_SOCIABILITY:
        base += AMENITY_HIGH_SOCIABILITY_BONUS

    social_n = social_meeting_count(rel)
    if rel.friendship >= FRIENDSHIP_DRIP_THRESHOLD:
        drip = (
            1
            if social_n > 0 and (social_n + 1) % FRIENDSHIP_DRIP_EVERY_N_SOCIAL == 0
            else 0
        )
        return AMENITY_FAMILIARITY_BUMP, drip

    k = FRIENDSHIP_K_EARLY if rel.friendship < CLOSE_FRIENDSHIP_MIN else FRIENDSHIP_K_LATE
    return AMENITY_FAMILIARITY_BUMP, _diminish(base, rel.friendship, k)


def _is_cooled(rel: Relationship) -> bool:
    if rel.peak_friendship < CLOSE_FRIENDSHIP_MIN:
        return False
    return rel.friendship <= rel.peak_friendship * REACTIVATION_COOL_FRACTION


def _apply_reactivation(
    rel: Relationship,
    context: str,
    friend_bump: int,
    days_apart: int,
) -> int:
    """After cooling, reunions crawl — they do not snap back to peak."""
    if friend_bump <= 0:
        return friend_bump
    if not _is_cooled(rel):
        return friend_bump
    if days_apart < REACTIVATION_MIN_DAYS_APART:
        return friend_bump
    if context == "visit":
        return min(friend_bump, REACTIVATION_VISIT_BUMP)
    if context in {"pub", "cafe", "shop"}:
        return REACTIVATION_AMENITY_BUMP
    return min(friend_bump, REACTIVATION_AMENITY_BUMP)


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


def append_bond_event(rel: Relationship, event: BondEvent) -> None:
    rel.bond_events.append(event)
    if len(rel.bond_events) > BOND_EVENT_LIMIT:
        rel.bond_events = rel.bond_events[-BOND_EVENT_LIMIT:]


def _origin_phrase(context: str | None) -> str:
    if context == "work":
        return "at work"
    if context == "pub":
        return "at the pub"
    if context == "cafe":
        return "at the cafe"
    if context == "shop":
        return "at the shop"
    if context == "visit":
        return "during a visit"
    if context == "other":
        return "around town"
    return "in town"


def _record_social_life_events(
    world: World,
    a,
    b,
    rel: Relationship,
    *,
    prev_friendship: int,
    was_cooled: bool,
    days_apart: int,
    friend_bump: int,
    context: str,
) -> None:
    """Record close/reunion milestones without changing friendship math."""
    from sim.systems.circumstances import record_life_event
    from sim.types import LifeEvent, LifeEventKind

    day = world.clock.day
    if (
        not rel.ever_close
        and prev_friendship < CLOSE_FRIENDSHIP_MIN
        and rel.friendship >= CLOSE_FRIENDSHIP_MIN
    ):
        rel.ever_close = True
        rel.became_close_day = day
        rel.close_context = context
        append_bond_event(
            rel,
            BondEvent(
                day,
                "became_close",
                f"Became close {_origin_phrase(context)}",
                context,
            ),
        )
        record_life_event(
            a,
            LifeEvent(
                LifeEventKind.BECAME_CLOSE,
                day,
                f"Became close with {b.name}",
                related_person_id=b.id,
            ),
        )
        record_life_event(
            b,
            LifeEvent(
                LifeEventKind.BECAME_CLOSE,
                day,
                f"Became close with {a.name}",
                related_person_id=a.id,
            ),
        )
    elif (
        was_cooled
        and rel.ever_close
        and friend_bump > 0
        and days_apart >= FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS
        and context in AMENITY_CONTEXT_NAMES
        and (rel.last_reunion_day < 0 or day - rel.last_reunion_day >= 28)
    ):
        # Sparse reunion notes for bonds that were once close.
        rel.last_reunion_day = day
        rel.cooling_noted = False  # allow a later cooling note after recovery fades
        append_bond_event(
            rel,
            BondEvent(
                day,
                "reunited",
                f"Reunited {_origin_phrase(context)}",
                context,
            ),
        )
        record_life_event(
            a,
            LifeEvent(
                LifeEventKind.REUNITED,
                day,
                f"Reunited with {b.name}",
                related_person_id=b.id,
            ),
        )
        record_life_event(
            b,
            LifeEvent(
                LifeEventKind.REUNITED,
                day,
                f"Reunited with {a.name}",
                related_person_id=a.id,
            ),
        )


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


def days_since_met(world: World, rel: Relationship) -> int:
    if rel.last_met_total_minutes < 0:
        return 10_000
    return max(0, (world.total_minutes() - rel.last_met_total_minutes) // MINUTES_PER_DAY)


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


def _place_phrase(place: str) -> str:
    if place == "visits":
        return "on visits"
    if place == "town":
        return "around town"
    return f"at the {place}"


def _mostly_place_line(rel: Relationship) -> str:
    place = dominant_meeting_place(rel)
    social = social_meeting_count(rel)
    # Prefer social meetings when describing where they keep meeting.
    count = social if social > 0 else rel.times_met
    if place is None:
        return f"Met {count} times"
    where = "via visits" if place == "visits" else f"at the {place}"
    return f"Met {count} times · mostly {where}"


def social_summary_lines(world: World, person_id: int) -> list[str]:
    """Short prose lines for the observer inspector — life-shaped, not a CRM."""
    from sim.systems.circumstances import relationship_history_lines

    lines: list[str] = []

    close = close_companions(world, person_id, limit=2)
    n_close = len(close_companions(world, person_id, limit=8))
    n_acq = len(work_acquaintances(world, person_id, limit=8))
    n_cool = len(stale_companions(world, person_id, limit=8))
    if n_close or n_acq or n_cool:
        lines.append(
            f"Social: {n_close} close · {n_acq} acquaintances · {n_cool} cooled"
        )

    if close:
        from sim.systems.observe import origin_summary_lines

        parts = [f"{world.people[oid].name} ({place})" for oid, _rel, place in close]
        lines.append("Close with: " + ", ".join(parts))
        # Detail the strongest close companion only.
        other_id, rel, place = close[0]
        lines.append(f"  {_mostly_place_line(rel)}")
        last_seen = days_since_met(world, rel)
        last_bit = "today" if last_seen == 0 else f"{last_seen} day{'s' if last_seen != 1 else ''} ago"
        lines.append(
            f"  Friendship {rel.friendship} · peak {rel.peak_friendship} · last seen {last_bit}"
        )
        for origin_line in origin_summary_lines(world, rel, person_id)[:2]:
            lines.append(f"  {origin_line}")
        if rel.peak_friendship > rel.friendship + 5:
            lines.append("  Used to be closer")
        elif (
            last_seen >= COOLING_LAST_SEEN_DAYS
            and rel.friendship < rel.peak_friendship
            and rel.peak_friendship >= CLOSE_FRIENDSHIP_MIN
        ):
            lines.append("  Cooling")
        elif (
            last_seen <= 1
            and rel.peak_friendship >= CLOSE_FRIENDSHIP_MIN
            and rel.friendship < rel.peak_friendship * REACTIVATION_COOL_FRACTION + 8
            and rel.friendship < rel.peak_friendship
            and rel.friendship >= CLOSE_FRIENDSHIP_MIN - 5
            and rel.peak_friendship - rel.friendship >= 8
        ):
            # Recently met again but still well below a prior peak.
            lines.append("  Started seeing each other again")
        for note in rel.story_notes[-1:]:
            other_name = world.people[other_id].name.split()[0]
            lines.append(f"  {other_name}: {note[0].lower() + note[1:]}")
        hist = relationship_history_lines(rel, world, person_id)
        # Avoid repeating origin lines already shown above.
        hist = [h for h in hist if not h.strip().startswith("Origin:")]
        if hist:
            lines.append("  History:")
            lines.extend(hist[:4])

    recurring = recurring_social(world, person_id, limit=1)
    if recurring:
        other_id, _rel, place = recurring[0]
        lines.append(f"Often sees: {world.people[other_id].name} {_place_phrase(place)}")

    work = work_acquaintances(world, person_id, limit=3)
    if work:
        names = ", ".join(world.people[oid].name for oid, _ in work)
        lines.append(f"At work knows: {names}")

    # Prefer a stale line when we did not already note "used to be closer" on a close friend.
    if not any(line.strip().startswith("Used to be closer") for line in lines):
        stale = stale_companions(world, person_id, limit=1)
        if stale:
            other_id, rel = stale[0]
            # Avoid repeating someone already listed as close.
            close_ids = {oid for oid, _, _ in close}
            if other_id not in close_ids:
                lines.append(f"Used to see: {world.people[other_id].name}")
                for note in rel.story_notes[-1:]:
                    lines.append(f"  {note}")

    return lines
