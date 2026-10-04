"""M6: circumstances and life changes that reshape opportunity, not friendship math."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sim.rng import make_rng
from sim.types import (
    CIRCUMSTANCE_NOTE_LIMIT,
    LIFE_EVENT_HISTORY_LIMIT,
    MOVE_DAILY_CHANCE,
    OVERWORKED_DAILY_CHANCE,
    OVERWORKED_MAX_DAYS,
    OVERWORKED_MIN_DAYS,
    RECENTLY_MOVED_DAYS,
    SICK_DAILY_CHANCE,
    SICK_MAX_DAYS,
    SICK_MIN_DAYS,
    UNEMPLOYED_DAILY_CHANCE,
    UNEMPLOYED_MAX_DAYS,
    UNEMPLOYED_MIN_DAYS,
    BuildingKind,
    Circumstance,
    CircumstanceKind,
    LifeEvent,
    LifeEventKind,
    Person,
)

if TYPE_CHECKING:
    from sim.world import World


def has_circumstance(person: Person, kind: CircumstanceKind) -> bool:
    return any(c.kind == kind for c in person.circumstances)


def active_circumstances(person: Person) -> list[Circumstance]:
    return list(person.circumstances)


def is_available_host(person: Person) -> bool:
    """Sick or newly moved people are poor visit hosts for a while."""
    return not (
        has_circumstance(person, CircumstanceKind.SICK)
        or has_circumstance(person, CircumstanceKind.RECENTLY_MOVED)
    )


_DURABLE_LIFE_KINDS = frozenset(
    {
        LifeEventKind.BECAME_SICK,
        LifeEventKind.RECOVERED,
        LifeEventKind.BECAME_UNEMPLOYED,
        LifeEventKind.JOB_CHANGED,
        LifeEventKind.MOVED_HOME,
        LifeEventKind.BECAME_OVERWORKED,
        LifeEventKind.OVERWORK_ENDED,
        LifeEventKind.SETTLED_HOME,
        LifeEventKind.STARTED_JOB,
        LifeEventKind.DIED,
        LifeEventKind.FRIEND_PASSED,
        LifeEventKind.ARRIVED,
        LifeEventKind.CHILD_SETTLED,
        LifeEventKind.TITLE_CHANGED,
    }
)


def record_life_event(person: Person, event: LifeEvent) -> None:
    """Append a life event. Social milestones may be throttled for cadence."""
    from sim.types import BECAME_CLOSE_LIFE_EVENT_GAP_DAYS

    # Reunions stay on bond_events only — they flooded citizen timelines.
    if event.kind == LifeEventKind.REUNITED:
        return

    if event.kind == LifeEventKind.BECAME_CLOSE:
        for prev in reversed(person.life_events):
            if prev.kind != LifeEventKind.BECAME_CLOSE:
                continue
            if event.day - prev.day < BECAME_CLOSE_LIFE_EVENT_GAP_DAYS:
                return
            break

    person.life_events.append(event)
    # Prefer retaining durable events when trimming the ring buffer.
    if len(person.life_events) > LIFE_EVENT_HISTORY_LIMIT:
        durable = [e for e in person.life_events if e.kind in _DURABLE_LIFE_KINDS]
        social = [e for e in person.life_events if e.kind not in _DURABLE_LIFE_KINDS]
        keep_social = LIFE_EVENT_HISTORY_LIMIT - len(durable)
        if keep_social < 0:
            person.life_events = durable[-LIFE_EVENT_HISTORY_LIMIT:]
        else:
            person.life_events = durable + social[-keep_social:]
    if event.kind in _DURABLE_LIFE_KINDS:
        _append_history_line(person, f"Day {event.day}: {event.detail}")


def _append_history_line(person: Person, line: str) -> None:
    if person.history and person.history[-1] == line:
        return
    person.history.append(line)
    if len(person.history) > 12:
        person.history = person.history[-12:]


def add_relationship_note(world: World, a_id: int, b_id: int, note: str) -> None:
    from sim.systems.social import append_bond_event, get_relationship
    from sim.types import BondEvent

    rel = get_relationship(world, a_id, b_id)
    if note in rel.story_notes:
        return
    rel.story_notes.append(note)
    if len(rel.story_notes) > CIRCUMSTANCE_NOTE_LIMIT:
        rel.story_notes = rel.story_notes[-CIRCUMSTANCE_NOTE_LIMIT:]
    day = world.clock.day
    append_bond_event(rel, BondEvent(day, "note", note, None))


def tick_circumstances(world: World) -> None:
    """Advance / end circumstances, then maybe start new ones. Call on day roll."""
    day = world.clock.day
    for person_id in sorted(world.people):
        person = world.people[person_id]
        _expire_circumstances(world, person, day)

    for person_id in sorted(world.people):
        person = world.people[person_id]
        rng = make_rng(world.seed, f"life-d{day}-p{person.id}")
        _maybe_start_circumstances(world, person, day, rng)


def _expire_circumstances(world: World, person: Person, day: int) -> None:
    remaining: list[Circumstance] = []
    for circ in person.circumstances:
        if day <= circ.end_day:
            remaining.append(circ)
            continue
        _on_circumstance_end(world, person, circ, day)
    person.circumstances = remaining


def _on_circumstance_end(
    world: World, person: Person, circ: Circumstance, day: int
) -> None:
    from sim.systems.chronicle import pick_phrase

    rng = make_rng(world.seed, f"chronicle-end-d{day}-p{person.id}")
    if circ.kind == CircumstanceKind.SICK:
        record_life_event(
            person,
            LifeEvent(LifeEventKind.RECOVERED, day, pick_phrase(rng, "recovered")),
        )
    elif circ.kind == CircumstanceKind.OVERWORKED:
        record_life_event(
            person,
            LifeEvent(
                LifeEventKind.OVERWORK_ENDED, day, pick_phrase(rng, "overwork_ended")
            ),
        )
    elif circ.kind == CircumstanceKind.UNEMPLOYED:
        _assign_new_job(world, person, day)
    elif circ.kind == CircumstanceKind.RECENTLY_MOVED:
        pass  # quiet fade; move already recorded


def _maybe_start_circumstances(world: World, person: Person, day: int, rng) -> None:
    # One new circumstance per person per day at most; prefer non-conflicting starts.
    if has_circumstance(person, CircumstanceKind.SICK):
        return
    if (
        not has_circumstance(person, CircumstanceKind.UNEMPLOYED)
        and not has_circumstance(person, CircumstanceKind.OVERWORKED)
        and rng.random() < SICK_DAILY_CHANCE
    ):
        days = rng.randint(SICK_MIN_DAYS, SICK_MAX_DAYS)
        _start_sick(world, person, day, days)
        return

    if has_circumstance(person, CircumstanceKind.UNEMPLOYED):
        return

    if (
        not has_circumstance(person, CircumstanceKind.OVERWORKED)
        and rng.random() < UNEMPLOYED_DAILY_CHANCE
    ):
        days = rng.randint(UNEMPLOYED_MIN_DAYS, UNEMPLOYED_MAX_DAYS)
        _start_unemployed(world, person, day, days)
        return

    if (
        not has_circumstance(person, CircumstanceKind.OVERWORKED)
        and not has_circumstance(person, CircumstanceKind.SICK)
        and rng.random() < OVERWORKED_DAILY_CHANCE
    ):
        days = rng.randint(OVERWORKED_MIN_DAYS, OVERWORKED_MAX_DAYS)
        _start_overworked(world, person, day, days)
        return

    if (
        not has_circumstance(person, CircumstanceKind.RECENTLY_MOVED)
        and rng.random() < MOVE_DAILY_CHANCE
    ):
        _try_move_home(world, person, day, rng)


def _start_sick(world: World, person: Person, day: int, days: int) -> None:
    from sim.systems.chronicle import pick_phrase

    rng = make_rng(world.seed, f"chronicle-sick-d{day}-p{person.id}")
    person.circumstances.append(
        Circumstance(
            CircumstanceKind.SICK,
            day,
            day + days - 1,
            pick_phrase(rng, "note_sick"),
        )
    )
    record_life_event(
        person,
        LifeEvent(LifeEventKind.BECAME_SICK, day, pick_phrase(rng, "became_sick")),
    )
    _note_contacts(world, person, pick_phrase(rng, "contact_ill"))


def _start_unemployed(world: World, person: Person, day: int, days: int) -> None:
    from sim.systems.chronicle import pick_phrase

    old_work = world.buildings[person.work_id].name
    rng = make_rng(world.seed, f"chronicle-unemp-d{day}-p{person.id}")
    person.circumstances.append(
        Circumstance(
            CircumstanceKind.UNEMPLOYED,
            day,
            day + days - 1,
            pick_phrase(rng, "note_unemployed", place=old_work),
        )
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.BECAME_UNEMPLOYED,
            day,
            pick_phrase(rng, "became_unemployed", place=old_work),
        ),
    )
    _note_contacts(world, person, pick_phrase(rng, "contact_left_work"))


def _start_overworked(world: World, person: Person, day: int, days: int) -> None:
    from sim.systems.chronicle import pick_phrase

    rng = make_rng(world.seed, f"chronicle-overwork-d{day}-p{person.id}")
    person.circumstances.append(
        Circumstance(
            CircumstanceKind.OVERWORKED,
            day,
            day + days - 1,
            pick_phrase(rng, "note_overworked"),
        )
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.BECAME_OVERWORKED,
            day,
            pick_phrase(rng, "became_overworked"),
        ),
    )


def _try_move_home(world: World, person: Person, day: int, rng) -> None:
    homes = [b for b in world.buildings.values() if b.kind == BuildingKind.HOME]
    loads = {h.id: 0 for h in homes}
    for other in world.people.values():
        loads[other.home_id] = loads.get(other.home_id, 0) + 1

    candidates = [
        h
        for h in homes
        if h.id != person.home_id and loads.get(h.id, 0) < h.capacity
    ]
    if not candidates:
        candidates = [h for h in homes if h.id != person.home_id]
    if not candidates:
        return

    candidates.sort(key=lambda h: (loads.get(h.id, 0), h.id))
    # Prefer a different street when possible.
    different_street = [
        h for h in candidates if h.street_name != world.buildings[person.home_id].street_name
    ]
    pool = different_street or candidates
    new_home = rng.choice(pool[: max(1, len(pool) // 2)] if len(pool) > 2 else pool)

    old = world.buildings[person.home_id]
    person.home_id = new_home.id
    person.habit_evening = None
    person.favorite_visit_id = None
    # Snap to new home at day roll so the next schedule starts from there.
    person.x = float(new_home.x)
    person.y = float(new_home.y)
    person.path.clear()
    person.path_index = 0
    person.move_progress = 0.0

    from sim.systems.chronicle import pick_phrase

    phrase_rng = make_rng(world.seed, f"chronicle-move-d{day}-p{person.id}")
    person.circumstances.append(
        Circumstance(
            CircumstanceKind.RECENTLY_MOVED,
            day,
            day + RECENTLY_MOVED_DAYS - 1,
            pick_phrase(phrase_rng, "note_moved", place=old.name),
        )
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.MOVED_HOME,
            day,
            pick_phrase(
                phrase_rng, "moved_home", old=old.name, new=new_home.name
            ),
        ),
    )
    _note_contacts(world, person, pick_phrase(phrase_rng, "contact_moved"))


def _assign_new_job(world: World, person: Person, day: int) -> None:
    workplaces = [
        b for b in world.buildings.values() if b.kind == BuildingKind.WORKPLACE
    ]
    loads = {w.id: 0 for w in workplaces}
    for other in world.people.values():
        if has_circumstance(other, CircumstanceKind.UNEMPLOYED) and other.id == person.id:
            continue
        if other.id == person.id:
            continue
        loads[other.work_id] = loads.get(other.work_id, 0) + 1

    candidates = [
        w
        for w in workplaces
        if w.id != person.work_id and loads.get(w.id, 0) < w.capacity
    ]
    if not candidates:
        candidates = [w for w in workplaces if w.id != person.work_id] or workplaces
    candidates.sort(key=lambda w: (loads.get(w.id, 0), w.id))
    rng = make_rng(world.seed, f"rehire-d{day}-p{person.id}")
    new_work = rng.choice(candidates[: max(1, len(candidates) // 2)])

    from sim.systems.chronicle import pick_phrase

    old_name = world.buildings[person.work_id].name
    person.work_id = new_work.id
    person.occupation = new_work.occupation or person.occupation
    phrase_rng = make_rng(world.seed, f"chronicle-job-d{day}-p{person.id}")
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.JOB_CHANGED,
            day,
            pick_phrase(
                phrase_rng, "job_changed", new=new_work.name, old=old_name
            ),
        ),
    )
    _note_contacts(world, person, pick_phrase(phrase_rng, "contact_job_change"))


def _note_contacts(world: World, person: Person, note: str) -> None:
    """Tag existing bonds so the inspector can explain cooler contact."""
    from sim.types import CLOSE_FRIENDSHIP_MIN

    for (a, b), rel in world.relationships.items():
        if person.id not in (a, b):
            continue
        if rel.times_met <= 0:
            continue
        if rel.peak_friendship < CLOSE_FRIENDSHIP_MIN and rel.familiarity < 20:
            continue
        other_id = b if a == person.id else a
        add_relationship_note(world, person.id, other_id, note)


def circumstance_summary_lines(person: Person, current_day: int | None = None) -> list[str]:
    if not person.circumstances:
        return []
    from sim.systems.chronicle import relative_day_phrase

    labels = {
        CircumstanceKind.SICK: "Under the weather",
        CircumstanceKind.UNEMPLOYED: "Between jobs",
        CircumstanceKind.OVERWORKED: "Worn thin by work",
        CircumstanceKind.RECENTLY_MOVED: "Newly settled",
    }
    lines = ["Circumstances:"]
    for circ in person.circumstances:
        label = labels.get(circ.kind, circ.kind.name.title())
        extra = f" — {circ.note}" if circ.note else ""
        if current_day is not None:
            until = relative_day_phrase(circ.end_day, current_day)
            if until == "today":
                until_bit = "through today"
            elif until == "yesterday":
                until_bit = "ending yesterday"
            else:
                # end_day in the future → phrase as days left
                left = circ.end_day - current_day
                until_bit = "through today" if left <= 0 else f"for {left} more day{'s' if left != 1 else ''}"
        else:
            until_bit = f"until day {circ.end_day}"
        lines.append(f"  {label}{extra} ({until_bit})")
    return lines


def recent_life_event_lines(
    person: Person, limit: int = 4, current_day: int | None = None
) -> list[str]:
    if not person.life_events:
        return []
    from sim.systems.chronicle import relative_day_phrase

    # Prefer durable life changes over frequent social milestones in the panel.
    life_change = {
        LifeEventKind.BECAME_SICK,
        LifeEventKind.RECOVERED,
        LifeEventKind.BECAME_UNEMPLOYED,
        LifeEventKind.JOB_CHANGED,
        LifeEventKind.MOVED_HOME,
        LifeEventKind.BECAME_OVERWORKED,
        LifeEventKind.OVERWORK_ENDED,
    }
    baseline = {LifeEventKind.SETTLED_HOME, LifeEventKind.STARTED_JOB}
    changes = [e for e in person.life_events if e.kind in life_change]
    social = [
        e for e in person.life_events if e.kind not in life_change and e.kind not in baseline
    ]
    chosen = changes[-(limit - 1) :] if limit > 1 else []
    remaining = limit - len(chosen)
    if remaining > 0:
        chosen = chosen + social[-remaining:]
    if not chosen:
        return []
    chosen.sort(key=lambda e: e.day)
    lines = ["Recent events:"]
    for event in chosen[-limit:]:
        if current_day is not None and current_day - event.day <= 14:
            when = relative_day_phrase(event.day, current_day)
        else:
            when = f"day {event.day}"
        lines.append(f"  {event.detail} — {when}")
    return lines


def relationship_history_lines(rel, world: World, viewer_id: int) -> list[str]:
    """Compact deterministic bond history for the inspector."""
    from sim.systems.observe import origin_summary_lines

    lines: list[str] = []
    lines.extend(f"  {line}" for line in origin_summary_lines(world, rel, viewer_id))
    if rel.ever_close or rel.peak_friendship >= 20:
        where = ""
        if rel.close_context:
            from sim.systems.social import place_clause

            where = f" {place_clause(rel.close_context)}"
        lines.append(f"  Grew close{where}")
    for note in rel.story_notes[-2:]:
        lines.append(f"  {note}")
    if (
        rel.peak_friendship >= 20
        and rel.friendship < rel.peak_friendship * 0.6
        and rel.friendship > 0
    ):
        lines.append("  They have been missing each other lately")
    other_id = rel.b_id if rel.a_id == viewer_id else rel.a_id
    for pid in (viewer_id, other_id):
        person = world.people[pid]
        for event in reversed(person.life_events[-8:]):
            if (
                event.kind == LifeEventKind.REUNITED
                and event.related_person_id in (viewer_id, other_id)
            ):
                lines.append("  Found each other again recently")
                return lines
    return lines
