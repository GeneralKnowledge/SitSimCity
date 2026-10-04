from __future__ import annotations

import pygame

from app import colors
from app.camera import Camera
from sim.systems.circumstances import circumstance_summary_lines, recent_life_event_lines
from sim.systems.observe import (
    citizen_timeline,
    relationship_detail_lines,
    timeline_lines,
)
from sim.systems.social import (
    close_companions,
    recurring_social,
    social_summary_lines,
    stale_companions,
)
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
    *,
    show_timeline: bool = False,
    focus_other_id: int | None = None,
    show_world_report: bool = False,
    world_report_lines: list[str] | None = None,
    day_cue_text: str | None = None,
) -> None:
    surface.fill(colors.BG)
    map_rect = pygame.Rect(0, 0, surface.get_width(), surface.get_height() - BAR_HEIGHT)
    map_surf = surface.subsurface(map_rect)

    _draw_tiles(map_surf, world, camera)
    _draw_buildings(map_surf, world, camera, small_font, selected_building_id)
    _draw_people(map_surf, world, camera, selected_id, following)
    if day_cue_text:
        _draw_day_cue(map_surf, day_cue_text, font)
    _draw_hud(
        surface,
        world,
        selected_id,
        selected_building_id,
        following,
        font,
        small_font,
        show_timeline=show_timeline,
        focus_other_id=focus_other_id,
        show_world_report=show_world_report,
        world_report_lines=world_report_lines,
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


def _draw_day_cue(
    surface: pygame.Surface, text: str, font: pygame.font.Font
) -> None:
    """Soft centered banner when the calendar day rolls while watching."""
    label = font.render(text, True, colors.DAY_CUE)
    pad_x, pad_y = 18, 8
    box = pygame.Rect(
        0,
        0,
        label.get_width() + pad_x * 2,
        label.get_height() + pad_y * 2,
    )
    box.centerx = surface.get_width() // 2
    box.y = 18
    pygame.draw.rect(surface, colors.DAY_CUE_DIM, box, border_radius=4)
    pygame.draw.rect(surface, colors.PANEL_BORDER, box, 1, border_radius=4)
    surface.blit(label, (box.x + pad_x, box.y + pad_y))


def _draw_hud(
    surface: pygame.Surface,
    world: World,
    selected_id: int | None,
    selected_building_id: int | None,
    following: bool,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    *,
    show_timeline: bool,
    focus_other_id: int | None,
    show_world_report: bool,
    world_report_lines: list[str] | None,
) -> None:
    width, height = surface.get_size()
    pygame.draw.rect(surface, colors.PANEL, (0, height - BAR_HEIGHT, width, BAR_HEIGHT))
    pygame.draw.line(
        surface,
        colors.PANEL_BORDER,
        (0, height - BAR_HEIGHT),
        (width, height - BAR_HEIGHT),
        1,
    )
    paused = "PAUSED" if world.clock.paused else "RUNNING"
    follow_bit = "  ·  FOLLOW" if following else ""
    status = (
        f"{paused}{follow_bit}   Speed {world.clock.speed:g}x   {world.clock.format_time()}   "
        f"Seed {world.seed}   Citizens {len(world.people)}"
    )
    surface.blit(font.render(status, True, colors.TEXT), (12, height - 36))
    help_text = (
        "Space pause  |  [ ] speed  |  D/+day  Y/+5d  |  F follow  |  O random  |  "
        "T timeline  |  J bond  |  I interesting  |  W report  |  Esc clear"
    )
    surface.blit(small_font.render(help_text, True, colors.MUTED), (12, height - 18))

    lines: list[str] | None = None
    if selected_id is not None and selected_id in world.people:
        lines = _person_inspector_lines(
            world,
            world.people[selected_id],
            following,
            show_timeline=show_timeline,
            focus_other_id=focus_other_id,
        )
    elif selected_building_id is not None and selected_building_id in world.buildings:
        lines = _building_inspector_lines(world, selected_building_id)

    if show_world_report and world_report_lines:
        _draw_panel(surface, world_report_lines, font, small_font, side="left")

    if not lines:
        return
    _draw_panel(surface, lines, font, small_font, side="right", following=following)


def _draw_panel(
    surface: pygame.Surface,
    lines: list[str],
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    *,
    side: str,
    following: bool = False,
) -> None:
    width, height = surface.get_size()
    # Compact follow panel is narrower so the town stays visible.
    if following and side == "right":
        panel_w = 280
    else:
        panel_w = 340 if side == "right" else 320
    panel_h = 20 + len(lines) * 15
    max_h = height - BAR_HEIGHT - 24
    if side == "right":
        panel = pygame.Rect(width - panel_w - 12, 12, panel_w, min(panel_h, max_h))
    else:
        panel = pygame.Rect(12, 12, panel_w, min(panel_h, max_h))
    pygame.draw.rect(surface, colors.PANEL, panel)
    pygame.draw.rect(surface, colors.PANEL_BORDER, panel, 1)
    y = panel.y + 10
    max_chars = 40 if following and side == "right" else 48
    for i, line in enumerate(lines):
        f = font if i == 0 else small_font
        color = colors.FOLLOW if (following and i == 0) else (colors.TEXT if i == 0 else colors.MUTED)
        surface.blit(f.render(line[:max_chars], True, color), (panel.x + 12, y))
        y += 17 if i == 0 else 15
        if y > panel.bottom - 16:
            break


def _person_inspector_lines(
    world: World,
    person: Person,
    following: bool,
    *,
    show_timeline: bool = False,
    focus_other_id: int | None = None,
) -> list[str]:
    # Follow mode defaults to a lean "sit with them" card.
    if following and focus_other_id is None and not show_timeline:
        return _compact_follow_lines(world, person)

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

    if focus_other_id is not None and focus_other_id in world.people:
        lines.append("— Bond focus (J cycles) —")
        lines.extend(relationship_detail_lines(world, person.id, focus_other_id))
    else:
        lines.extend(social_summary_lines(world, person.id))
        lines.extend(recent_life_event_lines(person, limit=4))

    if show_timeline:
        entries = citizen_timeline(world, person.id, limit=14)
        lines.extend(timeline_lines(entries, heading="Life timeline (T):"))

    lines.append("Observer only — no orders.")
    return lines


def _compact_follow_lines(world: World, person: Person) -> list[str]:
    """Lean inhabit card: where they are, what's on today, who matters."""
    home = world.buildings[person.home_id]
    work = world.buildings[person.work_id]
    activity = person.activity.name.replace("_", " ").title()
    lines = [
        f"{person.name}  ·  FOLLOWING",
        f"{person.occupation} · age {person.age}",
        f"Now: {activity}",
        f"Home · {home.name}   Work · {work.name}",
    ]
    if person.plan_notes:
        lines.append("Today: " + "; ".join(person.plan_notes))
    lines.extend(circumstance_summary_lines(person))
    lines.extend(_compact_social_lines(world, person.id))
    lines.extend(recent_life_event_lines(person, limit=3))
    lines.append("Sit with them — T timeline · J bond")
    return lines


def _compact_social_lines(world: World, person_id: int) -> list[str]:
    """Short social snapshot without CRM-style trait dumps."""
    lines: list[str] = []
    close = close_companions(world, person_id, limit=2)
    if close:
        parts = [f"{world.people[oid].name} ({place})" for oid, _rel, place in close]
        lines.append("Close: " + ", ".join(parts))
        _oid, rel, _place = close[0]
        from sim.systems.observe import origin_summary_lines

        for origin_line in origin_summary_lines(world, rel, person_id)[:3]:
            # Skip raw-count lines; keep origin + soft work prose.
            if origin_line.startswith("Social meetings:"):
                continue
            lines.append(f"  {origin_line}")
    recurring = recurring_social(world, person_id, limit=1)
    if recurring:
        other_id, _rel, place = recurring[0]
        where = "via visits" if place == "visits" else f"at the {place}"
        lines.append(f"Often sees: {world.people[other_id].name} {where}")
    close_ids = {oid for oid, _, _ in close}
    stale = stale_companions(world, person_id, limit=1)
    if stale and stale[0][0] not in close_ids:
        lines.append(f"Used to see: {world.people[stale[0][0]].name}")
    if not lines:
        lines.append("Quiet social life for now")
    return lines


def focusable_others(world: World, person_id: int) -> list[int]:
    """Close then cooled companions — for J cycling."""
    ids: list[int] = []
    for oid, _, _ in close_companions(world, person_id, limit=8):
        ids.append(oid)
    for oid, _ in stale_companions(world, person_id, limit=8):
        if oid not in ids:
            ids.append(oid)
    return ids


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
