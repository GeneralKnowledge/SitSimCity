from __future__ import annotations

import random

FIRST_NAMES = (
    "Alice",
    "Bob",
    "Carol",
    "Dave",
    "Eve",
    "Frank",
    "Grace",
    "Hank",
    "Ivy",
    "Jack",
    "Kate",
    "Leo",
    "Mary",
    "Nina",
    "Owen",
    "Paula",
    "Quinn",
    "Ruth",
    "Sam",
    "Tina",
    "Uma",
    "Vince",
    "Wendy",
    "Xander",
    "Yvonne",
    "Zane",
    "Amy",
    "Ben",
    "Clara",
    "Dan",
    "Elena",
    "Felix",
    "Gina",
    "Hugo",
    "Iris",
    "Jon",
    "Lara",
    "Miles",
    "Nora",
    "Otto",
    "Piper",
    "Rosa",
    "Seth",
    "Tess",
    "Ulysses",
    "Vera",
    "Will",
    "Zoe",
)

LAST_NAMES = (
    "Miller",
    "Williams",
    "Brown",
    "Jones",
    "Taylor",
    "Clark",
    "Harris",
    "Lewis",
    "Walker",
    "Hall",
    "Allen",
    "Young",
    "King",
    "Wright",
    "Scott",
    "Green",
    "Baker",
    "Adams",
    "Nelson",
    "Hill",
    "Moore",
    "Cooper",
    "Reed",
    "Cook",
    "Morgan",
    "Bell",
    "Murphy",
    "Bailey",
    "Rivera",
    "Parker",
)

STREET_NAMES = (
    "Oak Street",
    "Maple Avenue",
    "River Road",
    "Westside Lane",
    "Chapel Street",
    "Mill Road",
    "Harbor Street",
    "Pine Court",
)

WORKPLACE_NAMES = (
    "Miller & Sons",
    "Harbor Logistics",
    "Westside Offices",
    "Town Ledger",
    "Brick & Board",
    "Northwind Workshop",
    "Riverfront Depot",
    "Chapel Street Press",
    "Pine Court Studio",
    "Oak Street Works",
    "Mill Road Dispatch",
    "Harbor Street Yard",
)

PUB_NAMES = (
    "The Crown & Anchor",
    "The Quiet Pint",
    "Evening Bell",
    "The Lantern Room",
)
SHOP_NAMES = (
    "Corner Goods",
    "Market Row",
    "Daily Provisions",
    "Harbor Mercantile",
)
CAFE_NAMES = (
    "Westside Cafe",
    "Steam & Crumb",
    "Morning Cup",
    "Mill Road Roast",
)

OCCUPATIONS = (
    "Clerk",
    "Accountant",
    "Courier",
    "Carpenter",
    "Baker",
    "Mechanic",
    "Secretary",
    "Stockkeeper",
    "Bookkeeper",
    "Assembler",
)


def person_name(rng: random.Random, used: set[str]) -> str:
    for _ in range(200):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if name not in used:
            used.add(name)
            return name
    # Extremely unlikely fallback
    name = f"Citizen {len(used) + 1}"
    used.add(name)
    return name
