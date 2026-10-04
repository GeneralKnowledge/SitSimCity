"""M7 observer helpers: timelines, ranking, diagnostics. No friendship retunes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sim.types import (
    ACQUAINTANCE_FAMILIARITY_MIN,
    ACQUAINTANCE_FRIENDSHIP_MAX,
    CLOSE_FRIENDSHIP_MIN,
    MINUTES_PER_DAY,
    TIMELINE_MAX_BECAME_CLOSE,
    TIMELINE_MAX_FIRST_MET,
    TIMELINE_MAX_REUNITED,
    LifeEventKind,
    Relationship,
)

_DURABLE_TIMELINE_KINDS = frozenset(
    {
        "became_sick",
        "recovered",
        "became_unemployed",
        "job_changed",
        "moved_home",
        "became_overworked",
        "overwork_ended",
        "settled_home",
        "started_job",
        "home",
        "work",
        "died",
        "friend_passed",
        "arrived",
        "child_settled",
        "title_changed",
    }
)

if TYPE_CHECKING:
    from sim.world import World


_CONTEXT_LABEL = {
    "work": "Work",
    "pub": "Pub",
    "cafe": "Café",
    "shop": "Shop",
    "visit": "Visits",
    "other": "Town",
}


@dataclass(frozen=True)
class TimelineEntry:
    day: int
    text: str
    kind: str = "event"


@dataclass(frozen=True)
class CitizenRank:
    person_id: int
    score: int
    life_events: int
    close: int
    cooled: int
    reunions: int
    job_changes: int
    moves: int
    illnesses: int


def advance_days(world: World, days: int) -> None:
    """Advance the simulation by whole calendar days (deterministic)."""
    if days <= 0:
        return
    world.step_minutes(days * MINUTES_PER_DAY)


def minutes_to_day(total_minutes: int) -> int:
    if total_minutes < 0:
        return 0
    return total_minutes // MINUTES_PER_DAY + 1


def context_label(context: str | None) -> str:
    if not context:
        return "Unknown"
    return _CONTEXT_LABEL.get(context, context.title())


def are_coworkers(world: World, a_id: int, b_id: int) -> bool:
    return world.people[a_id].work_id == world.people[b_id].work_id


def origin_summary_lines(
    world: World,
    rel: Relationship,
    viewer_id: int,
    *,
    verbose_work: bool = False,
) -> list[str]:
    """Accurate origin wording — never infer from meeting-count majority.

    Default inspector softens work-colocation noise into prose. Pass
    ``verbose_work=True`` for diagnostic raw counts.
    """
    from sim.systems.social import dominant_meeting_place, social_meeting_count

    lines: list[str] = []
    origin = rel.origin_context
    lines.append(f"Origin: {context_label(origin)}")

    social = social_meeting_count(rel)
    if verbose_work:
        lines.append(f"Social meetings: {social}")

    other_id = rel.b_id if rel.a_id == viewer_id else rel.a_id
    coworkers = are_coworkers(world, viewer_id, other_id)
    if verbose_work and rel.meetings_work > 0:
        lines.append(
            f"Work colocations: {rel.meetings_work} (familiarity only; no friendship)"
        )
    elif rel.meetings_work > 0:
        if coworkers:
            lines.append("Often at work together")
        elif origin != "work":
            lines.append("Later overlap: shared workplace time")
        else:
            lines.append("Shared workplace time (familiarity)")

    place = dominant_meeting_place(rel)
    if place and social > 0:
        place_label = "Visits" if place == "visits" else place.title()
        lines.append(f"Frequent social place: {place_label}")

    if coworkers:
        lines.append("Currently coworkers")

    return lines


def _dedupe_timeline(entries: list[TimelineEntry]) -> list[TimelineEntry]:
    deduped: list[TimelineEntry] = []
    seen: set[tuple[int, str]] = set()
    for entry in entries:
        key = (entry.day, entry.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _cap_timeline_kinds(entries: list[TimelineEntry]) -> list[TimelineEntry]:
    """Keep durable events; cap noisy social milestones for readability."""
    durable = [e for e in entries if e.kind in _DURABLE_TIMELINE_KINDS]
    close = [e for e in entries if e.kind == "became_close"][-TIMELINE_MAX_BECAME_CLOSE:]
    reunited = [e for e in entries if e.kind == "reunited"][-TIMELINE_MAX_REUNITED:]
    first_met = [e for e in entries if e.kind == "first_met"][-TIMELINE_MAX_FIRST_MET:]
    other = [
        e
        for e in entries
        if e.kind
        not in _DURABLE_TIMELINE_KINDS
        and e.kind not in {"became_close", "reunited", "first_met"}
    ]
    merged = durable + close + reunited + first_met + other
    merged.sort(key=lambda e: (e.day, e.text))
    return _dedupe_timeline(merged)


def citizen_timeline(world: World, person_id: int, limit: int = 24) -> list[TimelineEntry]:
    """Chronological life timeline from recorded facts + initial placement."""
    person = world.people[person_id]
    entries: list[TimelineEntry] = []

    # Prefer persisted day-1 events; fall back to synthesis for older worlds.
    has_settled = any(e.kind == LifeEventKind.SETTLED_HOME for e in person.life_events)
    has_started = any(e.kind == LifeEventKind.STARTED_JOB for e in person.life_events)
    if not has_settled:
        from sim.systems.chronicle import pick_phrase
        from sim.rng import make_rng

        home = world.buildings[person.home_id]
        frng = make_rng(world.seed, f"chronicle-tl-home-p{person_id}")
        entries.append(
            TimelineEntry(1, pick_phrase(frng, "settled_home", place=home.name), "home")
        )
    if not has_started:
        from sim.systems.chronicle import pick_phrase
        from sim.rng import make_rng

        work = world.buildings[person.work_id]
        frng = make_rng(world.seed, f"chronicle-tl-work-p{person_id}")
        entries.append(
            TimelineEntry(1, pick_phrase(frng, "started_job", place=work.name), "work")
        )

    for event in person.life_events:
        kind = event.kind.name.lower()
        text = event.detail
        if event.kind == LifeEventKind.SETTLED_HOME:
            text = event.detail
            kind = "settled_home"
        elif event.kind == LifeEventKind.STARTED_JOB:
            text = event.detail
            kind = "started_job"
        entries.append(TimelineEntry(event.day, text, kind))

    # First meetings from bond events (reunions live on bonds, not citizen log).
    from sim.systems.chronicle import pick_phrase
    from sim.rng import make_rng

    for (a, b), rel in world.relationships.items():
        if person_id not in (a, b):
            continue
        other_id = b if a == person_id else a
        other = world.people[other_id]
        for be in rel.bond_events:
            if be.kind == "first_met":
                # Prefer bond detail; prefix with the other person's name.
                entries.append(
                    TimelineEntry(
                        be.day,
                        f"Met {other.name} — {be.detail[0].lower() + be.detail[1:]}",
                        "first_met",
                    )
                )
            elif be.kind == "became_close":
                crng = make_rng(
                    world.seed, f"chronicle-tl-close-d{be.day}-p{person_id}-{other_id}"
                )
                entries.append(
                    TimelineEntry(
                        be.day,
                        pick_phrase(crng, "became_close_with", name=other.name),
                        "became_close",
                    )
                )
            elif be.kind == "reunited":
                crng = make_rng(
                    world.seed, f"chronicle-tl-reun-d{be.day}-p{person_id}-{other_id}"
                )
                entries.append(
                    TimelineEntry(
                        be.day,
                        pick_phrase(crng, "reunited_with", name=other.name),
                        "reunited",
                    )
                )

    entries = _cap_timeline_kinds(_dedupe_timeline(entries))
    if limit > 0:
        return entries[-limit:]
    return entries


def relationship_timeline(
    world: World, a_id: int, b_id: int, limit: int = 20
) -> list[TimelineEntry]:
    from sim.systems.social import days_since_met, get_relationship, social_meeting_count

    rel = get_relationship(world, a_id, b_id)
    entries: list[TimelineEntry] = []
    for be in rel.bond_events:
        entries.append(TimelineEntry(be.day, be.detail, be.kind))

    # Status snapshot lines (not invented history) — no friendship CRM dump.
    if rel.first_met_total_minutes >= 0:
        from sim.systems.chronicle import relative_day_phrase

        gap = days_since_met(world, rel)
        if gap >= 10_000:
            last_bit = "never"
        else:
            last_bit = relative_day_phrase(world.clock.day - gap, world.clock.day)
        work_bit = ""
        if rel.meetings_work > 0 and are_coworkers(world, a_id, b_id):
            work_bit = " · often at work together"
        elif rel.meetings_work > 0:
            work_bit = " · some workplace overlap"
        entries.append(
            TimelineEntry(
                world.clock.day,
                f"Last seen {last_bit}{work_bit}",
                "status",
            )
        )
        if gap >= 3 and rel.peak_friendship >= CLOSE_FRIENDSHIP_MIN:
            entries.append(
                TimelineEntry(
                    world.clock.day,
                    f"{gap} days since last meeting",
                    "gap",
                )
            )

    entries.sort(key=lambda e: (e.day, e.kind, e.text))
    deduped = _dedupe_timeline(entries)
    if limit > 0:
        return deduped[-limit:]
    return deduped


def timeline_lines(
    entries: list[TimelineEntry],
    heading: str = "Timeline:",
    *,
    current_day: int | None = None,
) -> list[str]:
    if not entries:
        return []
    from sim.systems.chronicle import relative_day_phrase

    lines = [heading]
    for entry in entries:
        if current_day is not None and current_day - entry.day <= 14:
            when = relative_day_phrase(entry.day, current_day)
            lines.append(f"  {when.capitalize()}: {entry.text}")
        else:
            lines.append(f"  Day {entry.day}: {entry.text}")
    return lines


def relationship_detail_lines(
    world: World, viewer_id: int, other_id: int
) -> list[str]:
    from sim.systems.social import days_since_met, get_relationship

    rel = get_relationship(world, viewer_id, other_id)
    other = world.people[other_id]
    lines = [f"Bond: {other.name}"]
    last = days_since_met(world, rel)
    if last >= 10_000:
        lines.append("Last seen: never")
    elif last == 0:
        lines.append("Last seen: today")
    elif last == 1:
        lines.append("Last seen: yesterday")
    else:
        lines.append(f"Last seen: {last} days ago")
    lines.extend(origin_summary_lines(world, rel, viewer_id))
    lines.extend(
        timeline_lines(
            relationship_timeline(world, viewer_id, other_id, limit=12),
            heading="Bond timeline:",
            current_day=world.clock.day,
        )
    )
    return lines


def rank_interesting_citizens(world: World, limit: int = 10) -> list[CitizenRank]:
    from sim.systems.social import close_companions, stale_companions

    ranked: list[CitizenRank] = []
    for person in world.people.values():
        life = person.life_events
        job_changes = sum(1 for e in life if e.kind == LifeEventKind.JOB_CHANGED)
        moves = sum(1 for e in life if e.kind == LifeEventKind.MOVED_HOME)
        illnesses = sum(1 for e in life if e.kind == LifeEventKind.BECAME_SICK)
        reunions = sum(1 for e in life if e.kind == LifeEventKind.REUNITED)
        close = len(close_companions(world, person.id, limit=20))
        cooled = len(stale_companions(world, person.id, limit=20))
        n_rel = sum(
            1
            for (a, b), rel in world.relationships.items()
            if person.id in (a, b) and rel.times_met > 0
        )
        # Weight durable life changes above reunion spam in the event log.
        score = (
            job_changes * 8
            + moves * 8
            + illnesses * 5
            + close * 4
            + cooled * 3
            + min(reunions, 4) * 2
            + min(len(life), 16)
            + min(n_rel, 12)
        )
        ranked.append(
            CitizenRank(
                person_id=person.id,
                score=score,
                life_events=len(life),
                close=close,
                cooled=cooled,
                reunions=reunions,
                job_changes=job_changes,
                moves=moves,
                illnesses=illnesses,
            )
        )
    ranked.sort(key=lambda r: (-r.score, r.person_id))
    return ranked[:limit]


def interesting_relationship_pairs(
    world: World, limit: int = 8
) -> list[tuple[int, int, int]]:
    """Return (score, a_id, b_id) for bonds with rich arcs."""
    scored: list[tuple[int, int, int]] = []
    for (a, b), rel in world.relationships.items():
        if rel.times_met <= 0:
            continue
        score = (
            len(rel.bond_events) * 3
            + rel.peak_friendship
            + (10 if rel.ever_close else 0)
            + (8 if rel.last_reunion_day >= 0 else 0)
            + len(rel.story_notes) * 4
            + (5 if rel.cooling_noted else 0)
        )
        if score < 15:
            continue
        scored.append((score, a, b))
    scored.sort(reverse=True)
    return scored[:limit]


def world_metrics(world: World) -> dict:
    from sim.systems.social import (
        close_companions,
        social_meeting_count,
        stale_companions,
    )

    close_keys: set[tuple[int, int]] = set()
    acquaintance = 0
    ever_close = 0
    reunions = 0
    ge20 = ge50 = eq100 = 0
    meetings = 0
    for (a, b), rel in world.relationships.items():
        meetings += rel.times_met
        if rel.ever_close:
            ever_close += 1
        if rel.last_reunion_day >= 0:
            reunions += 1
        if rel.friendship >= 100:
            eq100 += 1
        if rel.friendship >= 50:
            ge50 += 1
        if rel.friendship >= CLOSE_FRIENDSHIP_MIN:
            ge20 += 1
        if (
            rel.familiarity >= ACQUAINTANCE_FAMILIARITY_MIN
            and rel.friendship <= ACQUAINTANCE_FRIENDSHIP_MAX
        ):
            acquaintance += 1

    for pid in world.people:
        for oid, rel, _ in close_companions(world, pid, limit=30):
            close_keys.add((min(pid, oid), max(pid, oid)))

    degrees = []
    zero_close = 0
    for pid in world.people:
        n = len(close_companions(world, pid, limit=30))
        degrees.append(n)
        if n == 0:
            zero_close += 1

    cooled = sum(len(stale_companions(world, pid, limit=30)) for pid in world.people)

    circ = Counter()
    life = Counter()
    for p in world.people.values():
        for c in p.circumstances:
            circ[c.kind.name] += 1
        for e in p.life_events:
            life[e.kind.name] += 1

    n = len(world.people)
    mean_deg = sum(degrees) / n if n else 0.0
    deaths = sum(1 for e in world.town_chronicle if e.kind == LifeEventKind.DIED)
    arrivals = sum(1 for e in world.town_chronicle if e.kind == LifeEventKind.ARRIVED)
    couples = sum(
        1
        for rel in world.relationships.values()
        if any(be.kind == "keeping_company" for be in rel.bond_events)
    )
    return {
        "day": world.clock.day,
        "population": n,
        "close_edges": len(close_keys),
        "mean_degree": mean_deg,
        "max_degree": max(degrees) if degrees else 0,
        "zero_close": zero_close,
        "acquaintance_edges": acquaintance,
        "ever_close_bonds": ever_close,
        "reunions": reunions,
        "ge20": ge20,
        "ge50": ge50,
        "eq100": eq100,
        "relationships": len(world.relationships),
        "meetings_total": meetings,
        "cooled_listings": cooled,
        "active_circumstances": dict(circ),
        "life_events": dict(life),
        "avg_life_events": (
            sum(len(p.life_events) for p in world.people.values()) / n if n else 0.0
        ),
        "town_deaths": deaths,
        "town_arrivals": arrivals,
        "keeping_company_pairs": couples,
    }


def world_report_lines(world: World) -> list[str]:
    m = world_metrics(world)
    lines = [
        f"WORLD — DAY {m['day']}",
        f"Population: {m['population']}",
        f"Town chronicle: {m['town_deaths']} deaths · {m['town_arrivals']} arrivals",
        f"Keeping company: {m['keeping_company_pairs']} pairs",
        "Relationships",
        f"  Close: {m['close_edges']}",
        f"  Acquaintance: {m['acquaintance_edges']}",
        f"  Ever-close: {m['ever_close_bonds']}",
        f"  Reunions: {m['reunions']}",
        f"  Mean/max degree: {m['mean_degree']:.2f} / {m['max_degree']}",
        f"  Zero-close: {m['zero_close']}  ≥20:{m['ge20']}  ≥50:{m['ge50']}  =100:{m['eq100']}",
        "Circumstances (active)",
    ]
    active = m["active_circumstances"]
    if active:
        for kind, count in sorted(active.items()):
            lines.append(f"  {kind}: {count}")
    else:
        lines.append("  (none)")
    lines.append("Most eventful citizens")
    for rank in rank_interesting_citizens(world, limit=5):
        p = world.people[rank.person_id]
        bits = []
        if rank.job_changes:
            bits.append(f"{rank.job_changes} job")
        if rank.moves:
            bits.append(f"{rank.moves} move")
        if rank.illnesses:
            bits.append(f"{rank.illnesses} ill")
        if rank.close:
            bits.append(f"{rank.close} close")
        if rank.cooled:
            bits.append(f"{rank.cooled} cooled")
        extra = ", ".join(bits) if bits else "quiet"
        lines.append(f"  {p.name} — {rank.life_events} events ({extra})")
    lines.append("Most interesting relationships")
    for score, a, b in interesting_relationship_pairs(world, limit=5):
        lines.append(
            f"  {world.people[a].name} ↔ {world.people[b].name} (score {score})"
        )
    if world.town_chronicle:
        lines.append("Recent town chronicle")
        for event in world.town_chronicle[-6:]:
            lines.append(f"  Day {event.day}: {event.detail}")
    return lines


def format_rank_table(world: World, limit: int = 8) -> list[str]:
    lines = ["Most eventful citizens"]
    for i, rank in enumerate(rank_interesting_citizens(world, limit=limit), start=1):
        p = world.people[rank.person_id]
        lines.append(
            f"{i}. {p.name}  score={rank.score}  events={rank.life_events}  "
            f"close={rank.close}  cooled={rank.cooled}  "
            f"jobs={rank.job_changes}  moves={rank.moves}  ill={rank.illnesses}"
        )
    return lines
