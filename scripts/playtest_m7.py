#!/usr/bin/env python3
"""M7 playtest protocol: follow lives across seeds/days; print observer reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.systems.observe import (
    advance_days,
    citizen_timeline,
    format_rank_table,
    interesting_relationship_pairs,
    relationship_detail_lines,
    timeline_lines,
    world_metrics,
    world_report_lines,
)
from sim.systems.social import close_companions, stale_companions
from sim.world import create_world

FOLLOW_SEEDS_DEFAULT = (7,)
MULTI_SEEDS = (1, 7, 13, 42, 100)


def _print(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def inspect_citizen(world, person_id: int) -> None:
    person = world.people[person_id]
    home = world.buildings[person.home_id].name
    work = world.buildings[person.work_id].name
    print(f"\n--- {person.name} (id={person_id}) age {person.age} ---")
    print(f"Home: {home}")
    print(f"Work: {work} · {person.occupation}")
    if person.circumstances:
        for c in person.circumstances:
            print(f"Circumstance: {c.kind.name} until day {c.end_day} ({c.note})")
    close = close_companions(world, person_id, limit=5)
    print(f"Close: {len(close)}")
    for oid, rel, place in close:
        print(
            f"  {world.people[oid].name} @ {place}  "
            f"f={rel.friendship}/peak={rel.peak_friendship}  "
            f"origin={rel.origin_context}"
        )
    cooled = stale_companions(world, person_id, limit=3)
    if cooled:
        print("Cooled:")
        for oid, rel in cooled:
            print(
                f"  {world.people[oid].name}  f={rel.friendship}/peak={rel.peak_friendship}"
            )
    print("\n".join(timeline_lines(citizen_timeline(world, person_id, limit=16))))
    if close:
        print("\n".join(relationship_detail_lines(world, person_id, close[0][0])))


def run_seed(seed: int, days: int, citizens: int = 50, follow: int = 5) -> dict:
    world = create_world(seed=seed, citizen_count=citizens)
    advance_days(world, days)
    metrics = world_metrics(world)
    ranked = format_rank_table(world, limit=follow)
    _print(f"SEED {seed} · {days} days")
    print("\n".join(world_report_lines(world)))
    print()
    print("\n".join(ranked))
    from sim.systems.observe import rank_interesting_citizens

    top = rank_interesting_citizens(world, limit=follow)
    for rank in top:
        inspect_citizen(world, rank.person_id)
    print("\nInteresting relationships:")
    for score, a, b in interesting_relationship_pairs(world, limit=5):
        print(f"\n# score={score}")
        print("\n".join(relationship_detail_lines(world, a, b)[:18]))
    return metrics


def compare_days(seed: int, day_list: list[int], citizens: int = 50) -> None:
    _print(f"QUANTITATIVE — seed {seed} at {day_list}")
    rows = []
    for days in day_list:
        world = create_world(seed=seed, citizen_count=citizens)
        advance_days(world, days)
        m = world_metrics(world)
        rows.append(m)
        print(
            f"d{days:3d}: close={m['close_edges']:3d} mean_deg={m['mean_degree']:.2f} "
            f"max={m['max_degree']:2d} zero={m['zero_close']:2d} "
            f">=20={m['ge20']:3d} >=50={m['ge50']:2d} =100={m['eq100']} "
            f"reunions={m['reunions']:3d} avg_life={m['avg_life_events']:.1f}"
        )
    out = ROOT / "artifacts" / "m7_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="M7 playtest / observer protocol")
    parser.add_argument(
        "--mode",
        choices=("a", "b", "c", "all", "metrics"),
        default="all",
        help="a=seed7 100d, b=seed7 200d, c=multi-seed 100d",
    )
    parser.add_argument("--citizens", type=int, default=50)
    parser.add_argument("--follow", type=int, default=5)
    args = parser.parse_args()

    if args.mode in ("a", "all"):
        run_seed(7, 100, citizens=args.citizens, follow=args.follow)
    if args.mode in ("b", "all"):
        run_seed(7, 200, citizens=args.citizens, follow=args.follow)
    if args.mode in ("c", "all"):
        for seed in MULTI_SEEDS:
            run_seed(seed, 100, citizens=args.citizens, follow=min(3, args.follow))
    if args.mode in ("metrics", "all"):
        compare_days(7, [30, 100, 200], citizens=args.citizens)
        _print("MULTI-SEED 100d metrics")
        for seed in MULTI_SEEDS:
            world = create_world(seed=seed, citizen_count=args.citizens)
            advance_days(world, 100)
            m = world_metrics(world)
            print(
                f"seed {seed:3d}: close={m['close_edges']:3d} mean={m['mean_degree']:.2f} "
                f"zero={m['zero_close']:2d} =100={m['eq100']} "
                f"avg_life={m['avg_life_events']:.1f} reunions={m['reunions']}"
            )


if __name__ == "__main__":
    main()
