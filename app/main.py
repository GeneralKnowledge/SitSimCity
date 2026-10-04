from __future__ import annotations

import argparse
import sys
import time

import pygame

from app.camera import Camera
from app.render import (
    BAR_HEIGHT,
    TILE,
    draw_world,
    focusable_others,
    pick_building,
    pick_person,
)
from sim.rng import make_rng
from sim.systems.observe import (
    advance_days,
    rank_interesting_citizens,
    world_report_lines,
)
from sim.types import SPEED_STEPS, Activity
from sim.world import World, create_world

DAY_CUE_SECONDS = 2.2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SitSimCity — tiny autonomous town prototype")
    parser.add_argument("--seed", type=int, default=42, help="Town generation seed")
    parser.add_argument("--citizens", type=int, default=80, help="Citizen count")
    parser.add_argument("--width", type=int, default=1120, help="Window width")
    parser.add_argument("--height", type=int, default=720, help="Window height")
    return parser.parse_args(argv)


def run(seed: int = 42, citizens: int = 80, width: int = 1120, height: int = 720) -> None:
    pygame.init()
    pygame.display.set_caption("SitSimCity — observer prototype")
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 16)
    small_font = pygame.font.SysFont("DejaVu Sans", 13)

    world = create_world(seed=seed, citizen_count=citizens)
    camera = Camera()
    _frame_city(camera, world, width, height)
    selected_id: int | None = None
    selected_building_id: int | None = None
    following = False
    show_timeline = False
    focus_other_id: int | None = None
    show_world_report = False
    report_lines: list[str] = []
    interesting_index = 0
    random_pick_nonce = 0
    dragging = False
    drag_last = (0, 0)
    last_day = world.clock.day
    day_cue_until = 0.0

    running = True
    while running:
        real_dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                prev_day = world.clock.day
                (
                    world,
                    selected_id,
                    selected_building_id,
                    following,
                    camera,
                    show_timeline,
                    focus_other_id,
                    show_world_report,
                    report_lines,
                    interesting_index,
                    random_pick_nonce,
                ) = _handle_key(
                    event,
                    world,
                    selected_id,
                    selected_building_id,
                    following,
                    camera,
                    width,
                    height,
                    citizens,
                    show_timeline,
                    focus_other_id,
                    show_world_report,
                    report_lines,
                    interesting_index,
                    random_pick_nonce,
                )
                if world.clock.day != prev_day:
                    day_cue_until = time.monotonic() + DAY_CUE_SECONDS
                    last_day = world.clock.day
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if event.pos[1] < height - BAR_HEIGHT:
                        selected_id = pick_person(world, camera, event.pos)
                        selected_building_id = None
                        focus_other_id = None
                        if selected_id is None:
                            following = False
                            building = pick_building(world, camera, event.pos)
                            selected_building_id = building.id if building else None
                    dragging = False
                elif event.button == 2 or event.button == 3:
                    following = False
                    dragging = True
                    drag_last = event.pos
                elif event.button == 4:
                    camera.adjust_zoom(1.1, event.pos)
                elif event.button == 5:
                    camera.adjust_zoom(1 / 1.1, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                dx = event.pos[0] - drag_last[0]
                dy = event.pos[1] - drag_last[1]
                camera.pan(-dx, -dy)
                drag_last = event.pos

        minutes = world.clock.consume_real_time(real_dt)
        if minutes > 0:
            world.step_minutes(min(minutes, 500))

        # M10: followed citizen may have exited — drop inhabit cleanly.
        if selected_id is not None and selected_id not in world.people:
            selected_id = None
            following = False
            focus_other_id = None
            show_timeline = False
        if focus_other_id is not None and focus_other_id not in world.people:
            focus_other_id = None

        if world.clock.day != last_day:
            day_cue_until = time.monotonic() + DAY_CUE_SECONDS
            last_day = world.clock.day

        if following and selected_id is not None and selected_id in world.people:
            person = world.people[selected_id]
            # Slightly closer framing while following so the day reads as a life.
            if camera.zoom < 1.35:
                camera.zoom = min(1.35, camera.zoom + real_dt * 0.4)
            # Soft follow with a mild lead while traveling.
            lead_x = person.x * TILE + TILE / 2
            lead_y = person.y * TILE + TILE / 2
            if person.activity == Activity.TRAVEL and person.path:
                tx, ty = person.path[-1]
                lead_x = lead_x * 0.7 + (tx * TILE + TILE / 2) * 0.3
                lead_y = lead_y * 0.7 + (ty * TILE + TILE / 2) * 0.3
            camera.ease_toward(
                lead_x,
                lead_y,
                width,
                height - BAR_HEIGHT,
                alpha=min(0.22, 0.08 + real_dt * 2.5),
            )

        day_cue_text = None
        if time.monotonic() < day_cue_until:
            day_cue_text = f"— Day {world.clock.day} —"

        draw_world(
            screen,
            world,
            camera,
            selected_id,
            selected_building_id,
            following,
            font,
            small_font,
            show_timeline=show_timeline,
            focus_other_id=focus_other_id,
            show_world_report=show_world_report,
            world_report_lines=report_lines,
            day_cue_text=day_cue_text,
        )
        pygame.display.flip()

    pygame.quit()


def _handle_key(
    event: pygame.event.Event,
    world: World,
    selected_id: int | None,
    selected_building_id: int | None,
    following: bool,
    camera: Camera,
    width: int,
    height: int,
    citizens: int,
    show_timeline: bool,
    focus_other_id: int | None,
    show_world_report: bool,
    report_lines: list[str],
    interesting_index: int,
    random_pick_nonce: int,
) -> tuple:
    if event.key == pygame.K_ESCAPE:
        return (
            world,
            None,
            None,
            False,
            camera,
            False,
            None,
            False,
            [],
            interesting_index,
            random_pick_nonce,
        )
    if event.key == pygame.K_SPACE:
        world.clock.toggle_pause()
    elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
        idx = SPEED_STEPS.index(world.clock.speed) if world.clock.speed in SPEED_STEPS else 1
        world.clock.speed = SPEED_STEPS[max(0, idx - 1)]
    elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS, pygame.K_PLUS):
        world.clock.cycle_speed()
    elif event.key == pygame.K_n:
        world = create_world(seed=world.seed + 1, citizen_count=citizens)
        selected_id = None
        selected_building_id = None
        following = False
        focus_other_id = None
        show_world_report = False
        report_lines = []
        show_timeline = False
        _frame_city(camera, world, width, height)
        pygame.display.set_caption(f"SitSimCity — seed {world.seed}")
    elif event.key == pygame.K_r:
        world = create_world(seed=world.seed, citizen_count=citizens)
        selected_id = None
        selected_building_id = None
        following = False
        focus_other_id = None
        show_world_report = False
        report_lines = []
        show_timeline = False
        _frame_city(camera, world, width, height)
    elif event.key == pygame.K_f:
        if selected_id is not None:
            following = not following
            if following:
                person = world.people[selected_id]
                camera.center_on(
                    person.x * TILE + TILE / 2,
                    person.y * TILE + TILE / 2,
                    width,
                    height - BAR_HEIGHT,
                )
        else:
            following = False
    elif event.key == pygame.K_d:
        # Advance one full day; pause so the observer can inspect.
        advance_days(world, 1)
        world.clock.paused = True
    elif event.key == pygame.K_y:
        advance_days(world, 5)
        world.clock.paused = True
    elif event.key == pygame.K_t:
        show_timeline = not show_timeline
    elif event.key == pygame.K_j:
        if selected_id is not None:
            others = focusable_others(world, selected_id)
            if others:
                if focus_other_id in others:
                    idx = others.index(focus_other_id)
                    focus_other_id = others[(idx + 1) % len(others)]
                else:
                    focus_other_id = others[0]
            else:
                focus_other_id = None
    elif event.key == pygame.K_i:
        ranked = rank_interesting_citizens(world, limit=12)
        if ranked:
            interesting_index = (interesting_index + 1) % len(ranked)
            selected_id = ranked[interesting_index].person_id
            selected_building_id = None
            focus_other_id = None
            following = True
            show_timeline = False
            person = world.people[selected_id]
            camera.center_on(
                person.x * TILE + TILE / 2,
                person.y * TILE + TILE / 2,
                width,
                height - BAR_HEIGHT,
            )
    elif event.key == pygame.K_o:
        # Random citizen — inhabit-first: follow on, timeline off.
        ids = sorted(world.people)
        if ids:
            random_pick_nonce += 1
            rng = make_rng(world.seed, f"ui-random-follow-{random_pick_nonce}")
            selected_id = rng.choice(ids)
            selected_building_id = None
            focus_other_id = None
            following = True
            show_timeline = False
            person = world.people[selected_id]
            if camera.zoom < 1.2:
                camera.zoom = 1.2
            camera.center_on(
                person.x * TILE + TILE / 2,
                person.y * TILE + TILE / 2,
                width,
                height - BAR_HEIGHT,
            )
    elif event.key == pygame.K_w:
        show_world_report = not show_world_report
        if show_world_report:
            report_lines = world_report_lines(world)
            print("\n".join(report_lines), flush=True)
    elif pygame.K_1 <= event.key <= pygame.K_7:
        world.clock.speed = SPEED_STEPS[event.key - pygame.K_1]
    return (
        world,
        selected_id,
        selected_building_id,
        following,
        camera,
        show_timeline,
        focus_other_id,
        show_world_report,
        report_lines,
        interesting_index,
        random_pick_nonce,
    )


def _frame_city(camera: Camera, world: World, width: int, height: int) -> None:
    camera.zoom = 1.0
    camera.center_on(
        (world.width * TILE) / 2,
        (world.height * TILE) / 2,
        width,
        height - BAR_HEIGHT,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run(seed=args.seed, citizens=args.citizens, width=args.width, height=args.height)


if __name__ == "__main__":
    main(sys.argv[1:])
