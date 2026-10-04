from __future__ import annotations

import random
from dataclasses import dataclass, field

from sim.generate import names
from sim.types import Building, BuildingKind, TileKind


@dataclass
class CityLayout:
    width: int
    height: int
    tiles: list[list[TileKind]]
    buildings: dict[int, Building] = field(default_factory=dict)
    street_of_row: dict[int, str] = field(default_factory=dict)
    street_of_col: dict[int, str] = field(default_factory=dict)


def generate_city(rng: random.Random, width: int = 48, height: int = 36) -> CityLayout:
    """Build a tiny road grid with homes, workplaces, and civic buildings."""
    tiles = [[TileKind.EMPTY for _ in range(width)] for _ in range(height)]
    street_names = list(names.STREET_NAMES)
    rng.shuffle(street_names)

    # Horizontal main roads and a few vertical connectors.
    h_roads = [6, 14, 22, 30]
    v_roads = [8, 18, 28, 38]
    street_of_row: dict[int, str] = {}
    street_of_col: dict[int, str] = {}

    for i, y in enumerate(h_roads):
        street_of_row[y] = street_names[i % len(street_names)]
        for x in range(2, width - 2):
            tiles[y][x] = TileKind.ROAD

    for i, x in enumerate(v_roads):
        street_of_col[x] = street_names[(i + 4) % len(street_names)]
        for y in range(2, height - 2):
            tiles[y][x] = TileKind.ROAD

    layout = CityLayout(
        width=width,
        height=height,
        tiles=tiles,
        street_of_row=street_of_row,
        street_of_col=street_of_col,
    )

    next_id = 1
    homes = _place_homes(rng, layout, count=20, start_id=next_id)
    next_id += len(homes)
    _register_buildings(layout, homes)

    workplaces = _place_workplaces(rng, layout, count=6, start_id=next_id)
    next_id += len(workplaces)
    _register_buildings(layout, workplaces)

    amenities = _place_amenities(rng, layout, start_id=next_id)
    _register_buildings(layout, amenities)

    return layout


def _register_buildings(layout: CityLayout, buildings: list[Building]) -> None:
    for building in buildings:
        layout.buildings[building.id] = building
        layout.tiles[building.y][building.x] = TileKind.BUILDING


def _road_neighbors(layout: CityLayout) -> list[tuple[int, int, str]]:
    """Candidate building lots: empty tiles orthogonally adjacent to a road."""
    lots: list[tuple[int, int, str]] = []
    for y in range(layout.height):
        for x in range(layout.width):
            if layout.tiles[y][x] != TileKind.EMPTY:
                continue
            street = ""
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= nx < layout.width and 0 <= ny < layout.height):
                    continue
                if layout.tiles[ny][nx] != TileKind.ROAD:
                    continue
                street = layout.street_of_row.get(ny) or layout.street_of_col.get(nx) or "Town Road"
                break
            if street:
                lots.append((x, y, street))
    return lots


def _claim_lot(
    rng: random.Random,
    lots: list[tuple[int, int, str]],
    occupied: set[tuple[int, int]],
) -> tuple[int, int, str] | None:
    rng.shuffle(lots)
    for x, y, street in lots:
        if (x, y) in occupied:
            continue
        occupied.add((x, y))
        return x, y, street
    return None


def _place_homes(
    rng: random.Random,
    layout: CityLayout,
    count: int,
    start_id: int,
) -> list[Building]:
    lots = _road_neighbors(layout)
    occupied: set[tuple[int, int]] = set()
    homes: list[Building] = []
    house_numbers: dict[str, int] = {}
    for i in range(count):
        claimed = _claim_lot(rng, lots, occupied)
        if claimed is None:
            break
        x, y, street = claimed
        n = house_numbers.get(street, 1)
        house_numbers[street] = n + 2
        homes.append(
            Building(
                id=start_id + i,
                kind=BuildingKind.HOME,
                name=f"{n} {street}",
                x=x,
                y=y,
                street_name=street,
                capacity=3,
            )
        )
    return homes


def _place_workplaces(
    rng: random.Random,
    layout: CityLayout,
    count: int,
    start_id: int,
) -> list[Building]:
    lots = _road_neighbors(layout)
    occupied = {(b.x, b.y) for b in layout.buildings.values()}
    names_pool = list(names.WORKPLACE_NAMES)
    rng.shuffle(names_pool)
    jobs = list(names.OCCUPATIONS)
    workplaces: list[Building] = []
    for i in range(count):
        claimed = _claim_lot(rng, lots, occupied)
        if claimed is None:
            break
        x, y, street = claimed
        workplaces.append(
            Building(
                id=start_id + i,
                kind=BuildingKind.WORKPLACE,
                name=names_pool[i % len(names_pool)],
                x=x,
                y=y,
                street_name=street,
                occupation=jobs[i % len(jobs)],
                capacity=12,
            )
        )
    return workplaces


def _place_amenities(
    rng: random.Random,
    layout: CityLayout,
    start_id: int,
) -> list[Building]:
    specs = (
        (BuildingKind.PUB, rng.choice(names.PUB_NAMES), 20),
        (BuildingKind.SHOP, rng.choice(names.SHOP_NAMES), 16),
        (BuildingKind.CAFE, rng.choice(names.CAFE_NAMES), 16),
        (BuildingKind.POLICE, "Police Station", 12),
        (BuildingKind.HOSPITAL, "Hospital", 12),
    )
    lots = _road_neighbors(layout)
    occupied = {(b.x, b.y) for b in layout.buildings.values()}
    buildings: list[Building] = []
    for i, (kind, name, capacity) in enumerate(specs):
        claimed = _claim_lot(rng, lots, occupied)
        if claimed is None:
            break
        x, y, street = claimed
        buildings.append(
            Building(
                id=start_id + i,
                kind=kind,
                name=name,
                x=x,
                y=y,
                street_name=street,
                capacity=capacity,
            )
        )
    return buildings
