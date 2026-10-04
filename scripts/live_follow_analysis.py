#!/usr/bin/env python3
"""M7.6: sit-with-citizen follow analysis via compact inhabit card snapshots.

Advances seeded worlds and prints the same compact follow / inspect surfaces
the pygame UI shows, so inhabit-vs-inspect can be judged without a human at
the keyboard.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.render import _compact_follow_lines, _person_inspector_lines
from sim.rng import make_rng
from sim.systems.observe import advance_days, citizen_timeline, timeline_lines
from sim.systems.social import close_companions, stale_companions
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
}


def pick_random(seed: int, world) -> int:
    rng = make_rng(seed, "follow-playtest-pick")
    return rng.choice(sorted(world.people))


def pick_quiet(world, exclude: int) -> int | None:
    for pid in sorted(world.people):
        if pid == exclude:
            continue
        if len(close_companions(world, pid, limit=5)) == 0:
            return pid
    scored = []
    for pid in sorted(world.people):
        if pid == exclude:
            continue
        p = world.people[pid]
        n = sum(1 for e in p.life_events if e.kind in DURABLE and e.day > 1)
        scored.append((n, len(close_companions(world, pid, limit=10)), pid))
    scored.sort()
    return scored[0][2] if scored else None


def snapshot(world, person_id: int, label: str) -> dict:
    person = world.people[person_id]
    compact = _compact_follow_lines(world, person)
    inspect = _person_inspector_lines(world, person, following=False)
    timeline = citizen_timeline(world, person_id, limit=14)
    close = close_companions(world, person_id, limit=8)
    cooled = stale_companions(world, person_id, limit=5)
    durable = [e for e in person.life_events if e.kind in DURABLE]

    print(f"\n{'=' * 72}")
    print(f"{label}: {person.name} (id={person_id}) · day {world.clock.day}")
    print(f"{'=' * 72}")
    print("--- COMPACT FOLLOW (inhabit) ---")
    for line in compact:
        print(line)
    print("--- FULL INSPECT (for contrast) ---")
    # Only show delta feel: line count + whether traits / work raw appear.
    print(f"(inspect lines={len(inspect)}; compact lines={len(compact)})")
    joined_c = "\n".join(compact)
    joined_i = "\n".join(inspect)
    print(f"compact has Traits: {'Traits' in joined_c}")
    print(f"inspect has Traits: {'Traits' in joined_i}")
    print(f"compact has Work colocations: {'Work colocations:' in joined_c}")
    print(f"inspect bond prose has Work colocations: {'Work colocations:' in joined_i}")
    print("--- TIMELINE (T) ---")
    for line in timeline_lines(timeline, heading="Life timeline:"):
        print(line)
    print(
        f"stats: close={len(close)} cooled={len(cooled)} "
        f"durable_life={len(durable)} tl_close="
        f"{sum(1 for e in timeline if e.kind == 'became_close')} "
        f"tl_reunited={sum(1 for e in timeline if e.kind == 'reunited')}"
    )
    return {
        "seed_label": label,
        "name": person.name,
        "day": world.clock.day,
        "compact_lines": len(compact),
        "inspect_lines": len(inspect),
        "close": len(close),
        "cooled": len(cooled),
        "durable": len(durable),
        "compact_text": joined_c,
    }


def run_follow(seed: int, days: int, role: str) -> dict:
    world = create_world(seed=seed, citizen_count=50)
    rid = pick_random(seed, world)
    pid = rid if role == "random" else (pick_quiet(world, rid) or rid)
    # Sit through the stretch in chunks so intermediate days are "lived".
    checkpoints = sorted({max(1, days // 3), max(1, (2 * days) // 3), days})
    prev = 0
    last = {}
    for cp in checkpoints:
        advance_days(world, cp - prev)
        prev = cp
        last = snapshot(world, pid, f"SEED {seed} · {cp}d · {role.upper()}")
    return last


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", action="store_true")
    args = parser.parse_args()
    rows = []
    if args.protocol:
        for seed, days, role in [
            (7, 30, "random"),
            (7, 30, "quiet"),
            (7, 60, "random"),
            (7, 60, "quiet"),
            (1, 60, "random"),
            (1, 60, "quiet"),
            (13, 60, "random"),
            (13, 60, "quiet"),
        ]:
            rows.append(run_follow(seed, days, role))
        print("\n" + "=" * 72)
        print("SUMMARY")
        print("=" * 72)
        for r in rows:
            print(
                f"{r['seed_label']:<32} {r['name']:<18} "
                f"compact={r['compact_lines']:2d} inspect={r['inspect_lines']:2d} "
                f"close={r['close']} cooled={r['cooled']} durable={r['durable']}"
            )
    else:
        run_follow(7, 60, "random")


if __name__ == "__main__":
    main()
