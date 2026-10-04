from __future__ import annotations

import argparse
import sys

import pygame

from app.camera import Camera
from app.render import BAR_HEIGHT, TILE, draw_world, pick_building, pick_person
from sim.types import SPEED_STEPS
from sim.world import World, create_world


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SitSimCity — tiny autonomous commute prototype")
    parser.add_argument("--seed", type=int, default=42, help="Town generation seed")
    parser.add_argument("--citizens", type=int, default=50, help="Citizen count")
    parser.add_argument("--width", type=int, default=1120, help="Window width")
    parser.add_argument("--height", type=int, default=720, help="Window height")
    return parser.parse_args(argv)


def run(seed: int = 42, citizens: int = 50, width: int = 1120, height: int = 720) -> None:
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
    dragging = False
    drag_last = (0, 0)

    running = True
    while running:
        real_dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                world, selected_id, selected_building_id, camera = _handle_key(
                    event,
                    world,
                    selected_id,
                    selected_building_id,
                    camera,
                    width,
                    height,
                    citizens,
                )
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if event.pos[1] < height - BAR_HEIGHT:
                        selected_id = pick_person(world, camera, event.pos)
                        selected_building_id = None
                        if selected_id is None:
                            building = pick_building(world, camera, event.pos)
                            selected_building_id = building.id if building else None
                    dragging = False
                elif event.button == 2 or event.button == 3:
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
        # Cap catch-up so extreme speeds stay responsive to input.
        if minutes > 0:
            world.step_minutes(min(minutes, 500))

        draw_world(
            screen,
            world,
            camera,
            selected_id,
            selected_building_id,
            font,
            small_font,
        )
        pygame.display.flip()

    pygame.quit()


def _handle_key(
    event: pygame.event.Event,
    world: World,
    selected_id: int | None,
    selected_building_id: int | None,
    camera: Camera,
    width: int,
    height: int,
    citizens: int,
) -> tuple[World, int | None, int | None, Camera]:
    if event.key == pygame.K_ESCAPE:
        return world, None, None, camera
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
        _frame_city(camera, world, width, height)
        pygame.display.set_caption(f"SitSimCity — seed {world.seed}")
    elif event.key == pygame.K_r:
        world = create_world(seed=world.seed, citizen_count=citizens)
        selected_id = None
        selected_building_id = None
        _frame_city(camera, world, width, height)
    elif event.key == pygame.K_f and selected_id is not None:
        person = world.people[selected_id]
        camera.center_on(
            person.x * TILE + TILE / 2,
            person.y * TILE + TILE / 2,
            width,
            height - BAR_HEIGHT,
        )
    elif pygame.K_1 <= event.key <= pygame.K_7:
        world.clock.speed = SPEED_STEPS[event.key - pygame.K_1]
    return world, selected_id, selected_building_id, camera


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
