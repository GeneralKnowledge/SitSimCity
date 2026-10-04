"""M10: lite death, adult replacements, soft couple / grown-child story beats.

No grief meters, romance sim, or vital statistics — chronicle texture only.
Friendship math and circumstance rates stay frozen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sim.generate import names
from sim.generate.tendencies import roll_tendencies
from sim.rng import make_rng
from sim.systems.chronicle import pick_phrase
from sim.systems.circumstances import record_life_event
from sim.systems.social import (
    append_bond_event,
    close_companions,
    get_relationship,
    relationship_key,
)
from sim.types import (
    CHILD_REPLACEMENT_CHANCE,
    CLOSE_FRIENDSHIP_MIN,
    COUPLE_NOTE_DAILY_CHANCE,
    DEATH_CHANCE_MID,
    DEATH_CHANCE_OLDER,
    DEATH_CHANCE_YOUNG,
    TITLE_BUMP_CHANCE,
    TOWN_CHRONICLE_LIMIT,
    Activity,
    BondEvent,
    BuildingKind,
    LifeEvent,
    LifeEventKind,
    Person,
)

if TYPE_CHECKING:
    from sim.world import World


def tick_lifecycle(world: World) -> None:
    """Call on day roll — after staleness/circumstances, before schedules."""
    day = world.clock.day
    _maybe_note_couples(world, day)
    _maybe_death_and_replace(world, day)


def _death_chance(age: int) -> float:
    if age >= 55:
        return DEATH_CHANCE_OLDER
    if age >= 45:
        return DEATH_CHANCE_MID
    return DEATH_CHANCE_YOUNG


def _maybe_death_and_replace(world: World, day: int) -> None:
    rng = make_rng(world.seed, f"lifecycle-death-d{day}")
    candidates: list[tuple[float, int]] = []
    for pid in sorted(world.people):
        person = world.people[pid]
        chance = _death_chance(person.age)
        if rng.random() < chance:
            candidates.append((chance, pid))
    if not candidates:
        return
    # At most one exit per day — pick the weightiest roll.
    candidates.sort(reverse=True)
    _apply_death(world, candidates[0][1], day)


def _apply_death(world: World, person_id: int, day: int) -> None:
    person = world.people[person_id]
    rng = make_rng(world.seed, f"lifecycle-apply-d{day}-p{person_id}")

    death_detail = pick_phrase(rng, "died", name=person.name.split()[0])
    _town_log(
        world,
        LifeEvent(
            LifeEventKind.DIED,
            day,
            f"{person.name}: {death_detail}",
            related_person_id=person_id,
        ),
    )

    friend_ids = [oid for oid, _rel, _place in close_companions(world, person_id, limit=4)]
    # Also tip anyone with ever-close peak who might not be "recent".
    for (a, b), rel in list(world.relationships.items()):
        if person_id not in (a, b):
            continue
        other = b if a == person_id else a
        if other in friend_ids:
            continue
        if rel.ever_close or rel.peak_friendship >= CLOSE_FRIENDSHIP_MIN:
            friend_ids.append(other)
    friend_ids = friend_ids[:4]

    first = person.name.split()[0]
    for fid in friend_ids:
        if fid not in world.people:
            continue
        friend = world.people[fid]
        frng = make_rng(world.seed, f"lifecycle-grief-d{day}-p{fid}-{person_id}")
        record_life_event(
            friend,
            LifeEvent(
                LifeEventKind.FRIEND_PASSED,
                day,
                pick_phrase(frng, "friend_passed", name=first),
                related_person_id=person_id,
            ),
        )
        rel = get_relationship(world, fid, person_id)
        note = pick_phrase(frng, "contact_friend_passed", name=first)
        if note not in rel.story_notes:
            rel.story_notes.append(note)
            if len(rel.story_notes) > 4:
                rel.story_notes = rel.story_notes[-4:]

    if rng.random() < TITLE_BUMP_CHANCE:
        _maybe_title_bump(world, person, day, rng)

    home_id = person.home_id
    work_id = person.work_id
    _remove_person(world, person_id)
    _spawn_replacement(world, day, home_id=home_id, preferred_work_id=work_id)


def _maybe_title_bump(world: World, departed: Person, day: int, rng) -> None:
    coworkers = [
        p
        for p in world.people.values()
        if p.id != departed.id and p.work_id == departed.work_id
    ]
    if not coworkers:
        return
    coworker = rng.choice(sorted(coworkers, key=lambda p: p.id))
    new_title = names.bump_occupation_title(coworker.occupation, rng)
    if new_title == coworker.occupation:
        return
    coworker.occupation = new_title
    trng = make_rng(world.seed, f"lifecycle-title-d{day}-p{coworker.id}")
    record_life_event(
        coworker,
        LifeEvent(
            LifeEventKind.TITLE_CHANGED,
            day,
            pick_phrase(trng, "title_changed", title=new_title),
        ),
    )


def _remove_person(world: World, person_id: int) -> None:
    world.people.pop(person_id, None)
    world._travel_targets.pop(person_id, None)
    drop_keys = [
        key for key in world.relationships if person_id in key
    ]
    for key in drop_keys:
        del world.relationships[key]
    # Clear visit favorites pointing at the departed.
    for other in world.people.values():
        if other.favorite_visit_id == person_id:
            other.favorite_visit_id = None
        if other.parent_ids and person_id in other.parent_ids:
            # Keep the story link ids even if a parent later dies; ids are historical.
            pass


def _spawn_replacement(
    world: World,
    day: int,
    *,
    home_id: int,
    preferred_work_id: int,
) -> Person:
    rng = make_rng(world.seed, f"lifecycle-spawn-d{day}-h{home_id}")
    used = {p.name for p in world.people.values()}
    workplaces = [
        b for b in world.buildings.values() if b.kind == BuildingKind.WORKPLACE
    ]
    work = world.buildings.get(preferred_work_id)
    if work is None or work.kind != BuildingKind.WORKPLACE:
        work = rng.choice(sorted(workplaces, key=lambda b: b.id))

    parents = None
    if rng.random() < CHILD_REPLACEMENT_CHANCE:
        parents = _pick_parent_pair(world, rng)

    if parents is not None:
        pa, pb = parents
        surname = rng.choice(
            [world.people[pa].name.split()[-1], world.people[pb].name.split()[-1]]
        )
        name = names.person_name_with_surname(rng, used, surname)
        # Adult child — functioning citizen, not a juvenile system.
        age = rng.randint(22, min(40, max(22, min(world.people[pa].age, world.people[pb].age) - 18)))
        parent_ids = (pa, pb) if pa < pb else (pb, pa)
    else:
        name = names.person_name(rng, used)
        age = rng.randint(22, 64)
        parent_ids = None

    person_id = world.next_person_id
    world.next_person_id += 1
    shift = "evening" if rng.random() < 0.25 else "day"
    home = world.buildings[home_id]
    person = Person(
        id=person_id,
        name=name,
        age=age,
        home_id=home_id,
        work_id=work.id,
        occupation=work.occupation or rng.choice(names.OCCUPATIONS),
        x=float(home.x),
        y=float(home.y),
        tendencies=roll_tendencies(rng),
        activity=Activity.SLEEP,
        wake_offset_minutes=rng.randint(0, 60),
        shift=shift,
        parent_ids=parent_ids,
    )
    world.people[person_id] = person

    place_rng = make_rng(world.seed, f"chronicle-place-p{person_id}-d{day}")
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.SETTLED_HOME,
            day,
            pick_phrase(place_rng, "settled_home", place=home.name),
        ),
    )
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.STARTED_JOB,
            day,
            pick_phrase(place_rng, "started_job", place=work.name),
        ),
    )

    if parent_ids is not None:
        pa, pb = parent_ids
        parent_a = world.people[pa]
        parent_b = world.people[pb]
        detail = pick_phrase(
            place_rng,
            "arrived_child",
            name=name.split()[0],
            parent_a=parent_a.name.split()[0],
            parent_b=parent_b.name.split()[0],
        )
        record_life_event(
            person,
            LifeEvent(LifeEventKind.ARRIVED, day, detail, related_person_id=pa),
        )
        for parent in (parent_a, parent_b):
            prng = make_rng(world.seed, f"lifecycle-child-d{day}-p{parent.id}")
            record_life_event(
                parent,
                LifeEvent(
                    LifeEventKind.CHILD_SETTLED,
                    day,
                    pick_phrase(prng, "child_settled", name=name.split()[0]),
                    related_person_id=person_id,
                ),
            )
        # Ensure the pair carries soft romance flavor when they gain a story child.
        _ensure_couple_note(world, pa, pb, day)
    else:
        record_life_event(
            person,
            LifeEvent(
                LifeEventKind.ARRIVED,
                day,
                pick_phrase(place_rng, "arrived"),
            ),
        )

    _town_log(
        world,
        LifeEvent(
            LifeEventKind.ARRIVED,
            day,
            f"{person.name}: {person.life_events[-1].detail}",
            related_person_id=person_id,
        ),
    )
    return person


def _pick_parent_pair(world: World, rng) -> tuple[int, int] | None:
    """Mutual close companions old enough to 'have' an adult child — story only."""
    pairs = mutual_close_pairs(world)
    suitable: list[tuple[int, int]] = []
    for a, b in pairs:
        pa, pb = world.people[a], world.people[b]
        if min(pa.age, pb.age) < 40:
            continue
        suitable.append((a, b))
    if not suitable:
        # Fall back to any mutual close pair.
        suitable = pairs
    if not suitable:
        return None
    return rng.choice(suitable)


def mutual_close_pairs(world: World) -> list[tuple[int, int]]:
    """Pairs where each appears in the other's close companions."""
    found: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for pid in sorted(world.people):
        close_ids = {oid for oid, _, _ in close_companions(world, pid, limit=5)}
        for oid in close_ids:
            if oid <= pid:
                continue
            other_close = {x for x, _, _ in close_companions(world, oid, limit=5)}
            if pid not in other_close:
                continue
            key = relationship_key(pid, oid)
            if key in seen:
                continue
            seen.add(key)
            found.append(key)
    return found


def _maybe_note_couples(world: World, day: int) -> None:
    """Surface-level romance: occasional 'keeping company' note on mutual close pairs."""
    rng = make_rng(world.seed, f"lifecycle-couple-d{day}")
    for a, b in mutual_close_pairs(world):
        if rng.random() >= COUPLE_NOTE_DAILY_CHANCE:
            continue
        _ensure_couple_note(world, a, b, day)


def _ensure_couple_note(world: World, a_id: int, b_id: int, day: int) -> None:
    rel = get_relationship(world, a_id, b_id)
    if any(be.kind == "keeping_company" for be in rel.bond_events):
        return
    rng = make_rng(world.seed, f"lifecycle-couple-note-d{day}-{a_id}-{b_id}")
    detail = pick_phrase(rng, "keeping_company")
    append_bond_event(
        rel,
        BondEvent(day=day, kind="keeping_company", detail=detail, context=None),
    )
    if detail not in rel.story_notes:
        rel.story_notes.append(detail)
        if len(rel.story_notes) > 4:
            rel.story_notes = rel.story_notes[-4:]


def _town_log(world: World, event: LifeEvent) -> None:
    world.town_chronicle.append(event)
    if len(world.town_chronicle) > TOWN_CHRONICLE_LIMIT:
        world.town_chronicle = world.town_chronicle[-TOWN_CHRONICLE_LIMIT:]
