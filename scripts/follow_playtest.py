#!/usr/bin/env python3
"""M7.5: follow randomly selected + quiet citizens across seeds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.rng import make_rng
from sim.systems.observe import (
    advance_days,
    citizen_timeline,
    relationship_detail_lines,
    timeline_lines,
)
from sim.systems.social import (
    close_companions,
    days_since_met,
    social_meeting_count,
    stale_companions,
    work_acquaintances,
)
from sim.types import LifeEventKind
from sim.world import create_world

DURABLE = {
    LifeEventKind.BECAME_SICK,
    LifeEventKind.RECOVERED,
    LifeEventKind.BECAME_UNEMPLOYED,
    LifeEventKind.JOB_CHANGED,
    LifeEventKind.MOVED_HOME,
    LifeEventKind.BECAME_OVERWORKED,
    LifeEventKind.OVERWORK_ENDED,
    LifeEventKind.SETTLED_HOME,
    LifeEventKind.STARTED_JOB,
}


def pick_random_citizen(seed: int, world) -> int:
    rng = make_rng(seed, "follow-playtest-pick")
    return rng.choice(sorted(world.people))


def pick_quiet_citizen(world, exclude: int) -> int | None:
    for pid in sorted(world.people):
        if pid == exclude:
            continue
        if len(close_companions(world, pid, limit=5)) == 0:
            return pid
    # Fallback: fewest life-change events
    scored = []
    for pid in sorted(world.people):
        if pid == exclude:
            continue
        p = world.people[pid]
        n = sum(1 for e in p.life_events if e.kind in DURABLE and e.day > 1)
        scored.append((n, len(close_companions(world, pid, limit=10)), pid))
    scored.sort()
    return scored[0][2] if scored else None


def inspect(world, person_id: int, label: str) -> dict:
    p = world.people[person_id]
    close = close_companions(world, person_id, limit=8)
    cooled = stale_companions(world, person_id, limit=5)
    work = work_acquaintances(world, person_id, limit=5)
    timeline = citizen_timeline(world, person_id, limit=14)
    became = sum(1 for e in timeline if e.kind == "became_close")
    reunited = sum(1 for e in timeline if e.kind == "reunited")
    durable_events = [e for e in p.life_events if e.kind in DURABLE]

    print(f"\n{'=' * 72}")
    print(f"{label}: {p.name} (id={person_id}) · day {world.clock.day}")
    print(f"{'=' * 72}")
    print(f"Age {p.age} · {p.occupation}")
    print(f"Home: {world.buildings[p.home_id].name}")
    print(f"Work: {world.buildings[p.work_id].name}")
    if p.circumstances:
        for c in p.circumstances:
            print(f"Circumstance: {c.kind.name} until {c.end_day} — {c.note}")
    else:
        print("Circumstances: none")
    print(f"Today: {'; '.join(p.plan_notes)}")
    print(
        f"Social: {len(close)} close · {len(work)} work acquaintances · {len(cooled)} cooled"
    )
    for oid, rel, place in close[:4]:
        print(
            f"  Close: {world.people[oid].name} @ {place}  "
            f"f={rel.friendship}/peak={rel.peak_friendship}  "
            f"origin={rel.origin_context}  "
            f"social={social_meeting_count(rel)} work_col={rel.meetings_work}  "
            f"last={days_since_met(world, rel)}d"
        )
    for oid, rel in cooled[:3]:
        print(
            f"  Cooled: {world.people[oid].name}  "
            f"f={rel.friendship}/peak={rel.peak_friendship}"
        )
    print("Durable life events:")
    for e in durable_events:
        print(f"  Day {e.day}: {e.detail}")
    print("\n".join(timeline_lines(timeline)))
    print(
        f"[cadence] timeline became_close={became} reunited={reunited} "
        f"(caps 3 / 1)"
    )

    if close:
        print("\n".join(relationship_detail_lines(world, person_id, close[0][0])))

    return {
        "name": p.name,
        "id": person_id,
        "close": len(close),
        "cooled": len(cooled),
        "timeline_close": became,
        "timeline_reunited": reunited,
        "durable": len([e for e in durable_events if e.day > 1]),
        "job_changes": sum(
            1 for e in durable_events if e.kind == LifeEventKind.JOB_CHANGED
        ),
        "moves": sum(1 for e in durable_events if e.kind == LifeEventKind.MOVED_HOME),
        "illnesses": sum(
            1 for e in durable_events if e.kind == LifeEventKind.BECAME_SICK
        ),
    }


def run_protocol() -> list[dict]:
    rows: list[dict] = []
    # Seed 7: 30d + 100d for random + quiet
    for days in (30, 100):
        world = create_world(seed=7, citizen_count=50)
        advance_days(world, days)
        rid = pick_random_citizen(7, world)
        qid = pick_quiet_citizen(world, rid)
        rows.append(
            {
                **inspect(world, rid, f"SEED 7 · {days}d · RANDOM"),
                "seed": 7,
                "days": days,
                "role": "random",
            }
        )
        if qid is not None:
            rows.append(
                {
                    **inspect(world, qid, f"SEED 7 · {days}d · QUIET"),
                    "seed": 7,
                    "days": days,
                    "role": "quiet",
                }
            )

    for seed in (1, 13, 42):
        world = create_world(seed=seed, citizen_count=50)
        advance_days(world, 100)
        rid = pick_random_citizen(seed, world)
        qid = pick_quiet_citizen(world, rid)
        rows.append(
            {
                **inspect(world, rid, f"SEED {seed} · 100d · RANDOM"),
                "seed": seed,
                "days": 100,
                "role": "random",
            }
        )
        if qid is not None:
            rows.append(
                {
                    **inspect(world, qid, f"SEED {seed} · 100d · QUIET"),
                    "seed": seed,
                    "days": 100,
                    "role": "quiet",
                }
            )

    world = create_world(seed=100, citizen_count=50)
    advance_days(world, 100)
    rid = pick_random_citizen(100, world)
    rows.append(
        {
            **inspect(world, rid, "SEED 100 · 100d · RANDOM"),
            "seed": 100,
            "days": 100,
            "role": "random",
        }
    )

    print("\n" + "=" * 72)
    print("SUMMARY TABLE")
    print("=" * 72)
    print(
        f"{'seed':>4} {'days':>4} {'role':<6} {'name':<18} "
        f"{'close':>5} {'cool':>4} {'tl_c':>4} {'tl_r':>4} "
        f"{'jobs':>4} {'move':>4} {'ill':>3}"
    )
    for r in rows:
        print(
            f"{r['seed']:4d} {r['days']:4d} {r['role']:<6} {r['name']:<18} "
            f"{r['close']:5d} {r['cooled']:4d} {r['timeline_close']:4d} "
            f"{r['timeline_reunited']:4d} {r['job_changes']:4d} "
            f"{r['moves']:4d} {r['illnesses']:3d}"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="M7.5 follow playtest protocol")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--days", type=int, default=100)
    parser.add_argument("--protocol", action="store_true", help="Full multi-seed protocol")
    args = parser.parse_args()
    if args.protocol or args.seed is None:
        run_protocol()
        return
    world = create_world(seed=args.seed, citizen_count=50)
    advance_days(world, args.days)
    rid = pick_random_citizen(args.seed, world)
    inspect(world, rid, f"SEED {args.seed} · {args.days}d · RANDOM")
    qid = pick_quiet_citizen(world, rid)
    if qid is not None:
        inspect(world, qid, f"SEED {args.seed} · {args.days}d · QUIET")


if __name__ == "__main__":
    main()
