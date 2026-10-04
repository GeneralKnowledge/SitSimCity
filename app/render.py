from __future__ import annotations

import pygame

from app import colors
from app.camera import Camera
from sim.systems.circumstances import circumstance_summary_lines, recent_life_event_lines
from sim.systems.social import social_summary_lines
from sim.types import BuildingKind, Person, TileKind
from sim.world import World

TILE = 16
BAR_HEIGHT = 52


def draw_world(
    surface: pygame.Surface,
    world: World,
    camera: Camera,
    selected_id: int | None,
    selected_building_id: int | None,
    following: bool,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
) -> None:
    surface.fill(colors.BG)
    map_rect = pygame.Rect(0, 0, surface.get_width(), surface.get_height() - BAR_HEIGHT)
    map_surf = surface.subsurface(map_rect)

    _draw_tiles(map_surf, world, camera)
    _draw_buildings(map_surf, world, camera, small_font, selected_building_id)
    _draw_people(map_surf, world, camera, selected_id, following)
    _draw_hud(
        surface,
        world,
        selected_id,
        selected_building_id,
        following,
        font,
        small_font,
    )


def _draw_tiles(surface: pygame.Surface, world: World, camera: Camera) -> None:
    tile_px = TILE * camera.zoom
    for y in range(world.height):
        for x in range(world.width):
            kind = world.tiles[y][x]
            if kind == TileKind.EMPTY:
                color = colors.EMPTY
            elif kind == TileKind.ROAD:
                color = colors.ROAD
            else:
                continue
            sx, sy = camera.world_to_screen(x * TILE, y * TILE)
            rect = pygame.Rect(sx, sy, tile_px + 1, tile_px + 1)
            if rect.colliderect(surface.get_rect()):
                pygame.draw.rect(surface, color, rect)


def _draw_buildings(
    surface: pygame.Surface,
    world: World,
    camera: Camera,
    small_font: pygame.font.Font,
    selected_building_id: int | None,
) -> None:
    tile_px = TILE * camera.zoom
    for building in world.buildings.values():
        sx, sy = camera.world_to_screen(building.x * TILE, building.y * TILE)
        rect = pygame.Rect(sx, sy, tile_px, tile_px)
        if not rect.colliderect(surface.get_rect()):
            continue
        fill = colors.BUILDING_FILL[building.kind]
        pygame.draw.rect(surface, fill, rect)
        border = colors.SELECT if building.id == selected_building_id else colors.PANEL_BORDER
        pygame.draw.rect(surface, border, rect, 2 if building.id == selected_building_id else 1)
        if camera.zoom >= 0.9:
            label = building.name if building.kind != BuildingKind.HOME else building.name.split()[0]
            text = small_font.render(label[:16], True, colors.TEXT)
            surface.blit(text, (sx + 2, sy - 12))


def _draw_people(
    surface: pygame.Surface,
    world: World,
    camera: Camera,
    selected_id: int | None,
    following: bool,
) -> None:
    size = max(3, int(6 * camera.zoom))
    for person in sorted(world.people.values(), key=lambda p: p.id):
        wx = person.x * TILE + TILE / 2
        wy = person.y * TILE + TILE / 2
        sx, sy = camera.world_to_screen(wx, wy)
        color = colors.PERSON_BY_ACTIVITY[person.activity]
        rect = pygame.Rect(int(sx - size / 2), int(sy - size / 2), size, size)
        pygame.draw.rect(surface, color, rect)
        if person.id == selected_id:
            outline = colors.FOLLOW if following else colors.SELECT
            pygame.draw.rect(surface, outline, rect.inflate(4, 4), 1)


def _draw_hud(
    surface: pygame.Surface,
    world: World,
    selected_id: int | None,
    selected_building_id: int | None,
    following: bool,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
) -> None:
    width, height = surface.get_size()
    bar = pygame.Rect(0, height - BAR_HEIGHT, width, BAR_HEIGHT)
    pygame.draw.rect(surface, colors.PANEL, bar)
    pygame.draw.line(surface, colors.PANEL_BORDER, (0, height - BAR_HEIGHT), (width, height - BAR_HEIGHT))

    paused = "PAUSED" if world.clock.paused else "PLAY"
    follow_bit = "   FOLLOWING" if following and selected_id is not None else ""
    status = (
        f"{paused}{follow_bit}   Speed {world.clock.speed:g}x   {world.clock.format_time()}   "
        f"Seed {world.seed}   Citizens {len(world.people)}"
    )
    surface.blit(font.render(status, True, colors.TEXT), (12, height - 36))
    help_text = (
        "Space pause  |  [ ] or 1-7 speed  |  N new  |  R reseed  |  "
        "F follow  |  Esc clear  |  Click inspect  |  Drag pan  |  Wheel zoom"
    )
    surface.blit(small_font.render(help_text, True, colors.MUTED), (12, height - 18))

    lines: list[str] | None = None
    if selected_id is not None and selected_id in world.people:
        lines = _person_inspector_lines(world, world.people[selected_id], following)
    elif selected_building_id is not None and selected_building_id in world.buildings:
        lines = _building_inspector_lines(world, selected_building_id)

    if not lines:
        return
    panel_h = 20 + len(lines) * 15
    panel = pygame.Rect(width - 300, 12, 288, min(panel_h, height - BAR_HEIGHT - 24))
    pygame.draw.rect(surface, colors.PANEL, panel)
    pygame.draw.rect(surface, colors.PANEL_BORDER, panel, 1)
    y = panel.y + 10
    for i, line in enumerate(lines):
        f = font if i == 0 else small_font
        color = colors.FOLLOW if (following and i == 0) else (colors.TEXT if i == 0 else colors.MUTED)
        surface.blit(f.render(line, True, color), (panel.x + 12, y))
        y += 17 if i == 0 else 15
        if y > panel.bottom - 16:
            break


def _person_inspector_lines(world: World, person: Person, following: bool) -> list[str]:
    home = world.buildings[person.home_id]
    work = world.buildings[person.work_id]
    t = person.tendencies
    lines = [
        person.name + ("  ·  FOLLOWING" if following else ""),
        f"Age {person.age}  ·  {person.occupation}",
        f"Home: {home.name}",
        f"Work: {work.name}",
        f"Activity: {person.activity.name.replace('_', ' ').title()}",
        (
            f"Traits  soc {t.sociability}  home {t.homebody}  "
            f"cafe {t.cafe_affinity}  shop {t.shop_affinity}"
        ),
        f"         pub {t.pub_affinity}  routine {t.routine_adherence}",
    ]
    if person.plan_notes:
        lines.append("Today: " + "; ".join(person.plan_notes))
    lines.extend(circumstance_summary_lines(person))
    lines.extend(social_summary_lines(world, person.id))
    lines.extend(recent_life_event_lines(person, limit=4))
    if person.history and not person.life_events:
        lines.append("History:")
        for item in person.history[-4:]:
            lines.append(f"· {item}")
    lines.append("Observer only — no orders.")
    return lines


def _building_inspector_lines(world: World, building_id: int) -> list[str]:
    building = world.buildings[building_id]
    present = world.people_at_building(building_id)
    lines = [
        building.name,
        f"{building.kind.name.title()} · {building.street_name}",
        f"Present: {len(present)}",
    ]
    for person in present[:6]:
        lines.append(f"· {person.name}")
    if len(present) > 6:
        lines.append(f"· …and {len(present) - 6} more")
    return lines


def pick_person(world: World, camera: Camera, screen_pos: tuple[int, int]) -> int | None:
    mx, my = screen_pos
    best_id: int | None = None
    best_dist = 14.0
    for person in world.people.values():
        wx = person.x * TILE + TILE / 2
        wy = person.y * TILE + TILE / 2
        sx, sy = camera.world_to_screen(wx, wy)
        dist = ((sx - mx) ** 2 + (sy - my) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_id = person.id
    return best_id


def pick_building(world: World, camera: Camera, screen_pos: tuple[int, int]):
    wx, wy = camera.screen_to_world(*screen_pos)
    tx, ty = int(wx // TILE), int(wy // TILE)
    return world.building_at(tx, ty)
