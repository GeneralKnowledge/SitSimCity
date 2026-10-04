from __future__ import annotations

import random

from sim.types import Tendencies


def roll_tendencies(rng: random.Random) -> Tendencies:
    """Sample ordinary leanings; occasionally accentuate one for visible archetypes."""
    t = Tendencies(
        sociability=rng.randint(8, 92),
        homebody=rng.randint(8, 92),
        cafe_affinity=rng.randint(5, 90),
        shop_affinity=rng.randint(5, 90),
        pub_affinity=rng.randint(5, 90),
        routine_adherence=rng.randint(15, 95),
    )
    if rng.random() > 0.30:
        return t

    archetype = rng.choice(
        ("pub", "cafe", "shop", "social", "homebody", "routine")
    )
    if archetype == "pub":
        return Tendencies(
            sociability=max(t.sociability, rng.randint(40, 80)),
            homebody=min(t.homebody, rng.randint(5, 35)),
            cafe_affinity=t.cafe_affinity,
            shop_affinity=t.shop_affinity,
            pub_affinity=rng.randint(78, 100),
            routine_adherence=min(t.routine_adherence, rng.randint(20, 55)),
        )
    if archetype == "cafe":
        return Tendencies(
            sociability=t.sociability,
            homebody=t.homebody,
            cafe_affinity=rng.randint(78, 100),
            shop_affinity=t.shop_affinity,
            pub_affinity=min(t.pub_affinity, 45),
            routine_adherence=t.routine_adherence,
        )
    if archetype == "shop":
        return Tendencies(
            sociability=t.sociability,
            homebody=t.homebody,
            cafe_affinity=t.cafe_affinity,
            shop_affinity=rng.randint(78, 100),
            pub_affinity=t.pub_affinity,
            routine_adherence=t.routine_adherence,
        )
    if archetype == "social":
        return Tendencies(
            sociability=rng.randint(80, 100),
            homebody=min(t.homebody, rng.randint(5, 40)),
            cafe_affinity=max(t.cafe_affinity, 40),
            shop_affinity=t.shop_affinity,
            pub_affinity=max(t.pub_affinity, 40),
            routine_adherence=min(t.routine_adherence, 60),
        )
    if archetype == "homebody":
        return Tendencies(
            sociability=min(t.sociability, rng.randint(5, 40)),
            homebody=rng.randint(80, 100),
            cafe_affinity=min(t.cafe_affinity, 40),
            shop_affinity=min(t.shop_affinity, 45),
            pub_affinity=min(t.pub_affinity, 25),
            routine_adherence=max(t.routine_adherence, 60),
        )
    return Tendencies(
        sociability=t.sociability,
        homebody=t.homebody,
        cafe_affinity=t.cafe_affinity,
        shop_affinity=t.shop_affinity,
        pub_affinity=t.pub_affinity,
        routine_adherence=rng.randint(80, 100),
    )
