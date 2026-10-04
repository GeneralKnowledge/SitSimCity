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


def record_life_event(person: Person, event: LifeEvent) -> None:
    person.life_events.append(event)
    if len(person.life_events) > LIFE_EVENT_HISTORY_LIMIT:
        person.life_events = person.life_events[-LIFE_EVENT_HISTORY_LIMIT:]
    _append_history_line(person, f"Day {event.day}: {event.detail}")


def _append_history_line(person: Person, line: str) -> None:
    if person.history and person.history[-1] == line:
        return
    person.history.append(line)
    if len(person.history) > 12:
        person.history = person.history[-12:]


def add_relationship_note(world: World, a_id: int, b_id: int, note: str) -> None:
    from sim.systems.social import get_relationship

    rel = get_relationship(world, a_id, b_id)
    if note in rel.story_notes:
        return
    rel.story_notes.append(note)
    if len(rel.story_notes) > CIRCUMSTANCE_NOTE_LIMIT:
        rel.story_notes = rel.story_notes[-CIRCUMSTANCE_NOTE_LIMIT:]


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
    if circ.kind == CircumstanceKind.SICK:
        record_life_event(
            person,
            LifeEvent(LifeEventKind.RECOVERED, day, "Recovered from illness"),
        )
    elif circ.kind == CircumstanceKind.OVERWORKED:
        record_life_event(
            person,
            LifeEvent(LifeEventKind.OVERWORK_ENDED, day, "Workload eased"),
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
        _start_overworked(person, day, days)
        return

    if (
        not has_circumstance(person, CircumstanceKind.RECENTLY_MOVED)
        and rng.random() < MOVE_DAILY_CHANCE
    ):
        _try_move_home(world, person, day, rng)


def _start_sick(world: World, person: Person, day: int, days: int) -> None:
    person.circumstances.append(
        Circumstance(CircumstanceKind.SICK, day, day + days - 1, "ill at home")
    )
    record_life_event(
        person,
        LifeEvent(LifeEventKind.BECAME_SICK, day, f"Fell ill ({days} days)"),
    )
    _note_contacts(world, person, "Became less available while ill")


def _start_unemployed(world: World, person: Person, day: int, days: int) -> None:
    old_work = world.buildings[person.work_id].name
    person.circumstances.append(
        Circumstance(
            CircumstanceKind.UNEMPLOYED,
            day,
            day + days - 1,
            f"left {old_work}",
        )
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.BECAME_UNEMPLOYED,
            day,
            f"Left job at {old_work}",
        ),
    )
    _note_contacts(world, person, "Became less available after leaving work")


def _start_overworked(person: Person, day: int, days: int) -> None:
    person.circumstances.append(
        Circumstance(
            CircumstanceKind.OVERWORKED,
            day,
            day + days - 1,
            "long work days",
        )
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.BECAME_OVERWORKED,
            day,
            f"Overworked ({days} days)",
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

    person.circumstances.append(
        Circumstance(
            CircumstanceKind.RECENTLY_MOVED,
            day,
            day + RECENTLY_MOVED_DAYS - 1,
            f"from {old.name}",
        )
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.MOVED_HOME,
            day,
            f"Moved from {old.name} to {new_home.name}",
        ),
    )
    _note_contacts(world, person, "Harder to catch after moving neighbourhood")


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

    old_name = world.buildings[person.work_id].name
    person.work_id = new_work.id
    person.occupation = new_work.occupation or person.occupation
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.JOB_CHANGED,
            day,
            f"Started work at {new_work.name} (left {old_name})",
        ),
    )
    _note_contacts(world, person, "Fewer shared workdays after a job change")


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


def circumstance_summary_lines(person: Person) -> list[str]:
    if not person.circumstances:
        return []
    labels = {
        CircumstanceKind.SICK: "Sick",
        CircumstanceKind.UNEMPLOYED: "Unemployed",
        CircumstanceKind.OVERWORKED: "Overworked",
        CircumstanceKind.RECENTLY_MOVED: "Recently moved",
    }
    lines = ["Circumstances:"]
    for circ in person.circumstances:
        label = labels.get(circ.kind, circ.kind.name.title())
        extra = f" — {circ.note}" if circ.note else ""
        lines.append(f"  {label}{extra} (until day {circ.end_day})")
    return lines


def recent_life_event_lines(person: Person, limit: int = 4) -> list[str]:
    if not person.life_events:
        return []
    lines = ["Recent events:"]
    for event in person.life_events[-limit:]:
        lines.append(f"  {event.detail} — day {event.day}")
    return lines


def relationship_history_lines(rel, world: World, viewer_id: int) -> list[str]:
    """Compact deterministic bond history for the inspector."""
    lines: list[str] = []
    social = (
        rel.meetings_pub + rel.meetings_cafe + rel.meetings_shop + rel.meetings_visit
    )
    if rel.meetings_work > 0 and rel.meetings_work >= social:
        lines.append("  Met through work")
    elif social > 0:
        lines.append("  Met socially in town")
    if rel.ever_close or rel.peak_friendship >= 20:
        lines.append("  Became close")
    for note in rel.story_notes[-2:]:
        lines.append(f"  {note}")
    if (
        rel.peak_friendship >= 20
        and rel.friendship < rel.peak_friendship * 0.6
        and rel.friendship > 0
    ):
        lines.append("  Friendship cooled with fewer meetings")
    # Recent reunion cue from life events of either person.
    other_id = rel.b_id if rel.a_id == viewer_id else rel.a_id
    for pid in (viewer_id, other_id):
        person = world.people[pid]
        for event in reversed(person.life_events[-6:]):
            if (
                event.kind == LifeEventKind.REUNITED
                and event.related_person_id in (viewer_id, other_id)
            ):
                lines.append("  Recent reunion")
                return lines
    return lines
