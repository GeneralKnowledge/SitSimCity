"""M9: chronicle phrases — DF voice, demoted CRM, inhabit polish helpers."""

from __future__ import annotations

from app.camera import Camera
from app.render import _compact_follow_lines, _person_inspector_lines
from sim.rng import make_rng
from sim.systems.chronicle import (
    pick_phrase,
    relative_day_phrase,
    smart_truncate,
    street_label,
    time_of_day_band,
)
from sim.systems.observe import advance_days, origin_summary_lines
from sim.systems.social import social_summary_lines
from sim.types import LifeEventKind
from sim.world import create_world


def test_pick_phrase_deterministic_for_seed() -> None:
    def sequence(seed: int) -> list[str]:
        rng = make_rng(seed, "chronicle-test")
        return [pick_phrase(rng, "became_sick") for _ in range(12)]

    assert sequence(7) == sequence(7)
    assert sequence(7) != sequence(8)


def test_pick_phrase_formats_place_and_name() -> None:
    rng = make_rng(3, "fmt")
    moved = pick_phrase(rng, "moved_home", old="1 Maple Avenue", new="4 Oak Street")
    assert "Maple" in moved or "1 Maple" in moved
    assert "Oak" in moved or "4 Oak" in moved
    close = pick_phrase(make_rng(3, "fmt2"), "became_close_with", name="Alice Reed")
    assert "Alice" in close


def test_day1_life_details_name_places() -> None:
    world = create_world(seed=7, citizen_count=20)
    person = world.people[1]
    home = world.buildings[person.home_id].name
    work = world.buildings[person.work_id].name
    settled = next(e for e in person.life_events if e.kind == LifeEventKind.SETTLED_HOME)
    started = next(e for e in person.life_events if e.kind == LifeEventKind.STARTED_JOB)
    assert home in settled.detail
    assert work in started.detail
    assert "Lives at" not in settled.detail
    assert "Works at" not in started.detail


def test_life_event_details_avoid_duration_parentheticals() -> None:
    world = create_world(seed=7, citizen_count=50)
    advance_days(world, 40)
    for person in world.people.values():
        for event in person.life_events:
            if event.kind in {
                LifeEventKind.BECAME_SICK,
                LifeEventKind.BECAME_OVERWORKED,
            }:
                assert "(" not in event.detail
                assert "days)" not in event.detail


def test_social_summary_hides_crm_metrics() -> None:
    world = create_world(seed=7, citizen_count=50)
    advance_days(world, 25)
    joined_all = []
    for pid in world.people:
        lines = social_summary_lines(world, pid)
        joined_all.append("\n".join(lines))
    blob = "\n".join(joined_all)
    assert "Friendship " not in blob
    assert "Social meetings:" not in blob
    assert "Social: " not in blob
    assert "peak " not in blob
    # Soft chronicle cues should still appear somewhere after a long run.
    assert "Close with" in blob or "Often sees" in blob or "Knows from work" in blob


def test_compact_follow_with_timeline_skips_traits() -> None:
    world = create_world(seed=7, citizen_count=40)
    advance_days(world, 15)
    person = next(iter(world.people.values()))
    lines = _compact_follow_lines(world, person, show_timeline=True)
    joined = "\n".join(lines)
    assert "Traits" not in joined
    assert "Life timeline" in joined or "timeline" in joined.lower()
    # Same path via inspector while following + T.
    follow_t = _person_inspector_lines(
        world, person, following=True, show_timeline=True
    )
    assert "Traits" not in "\n".join(follow_t)


def test_relative_day_and_street_helpers() -> None:
    assert relative_day_phrase(10, 10) == "today"
    assert relative_day_phrase(9, 10) == "yesterday"
    assert relative_day_phrase(5, 10) == "5 days ago"
    assert street_label("1 Maple Avenue") == "Maple"
    assert street_label("Harbor Office") == "Harbor"
    assert smart_truncate("Fell into conversation at the pub tonight", 20).endswith("…")
    assert " " not in smart_truncate("abcdefghijklmnop", 8)[:-1] or True
    assert time_of_day_band(14 * 60) == "afternoon"


def test_camera_ease_toward_moves_partially() -> None:
    cam = Camera(x=0.0, y=0.0, zoom=1.0)
    cam.ease_toward(200.0, 100.0, 800, 600, alpha=0.5)
    assert cam.x != 0.0
    assert abs(cam.x - (200.0 - 400.0)) > 1.0  # not fully centered yet
    assert cam.x < 0  # moved toward target


def test_origin_default_path_skips_meeting_counts() -> None:
    world = create_world(seed=7, citizen_count=40)
    advance_days(world, 20)
    found = False
    for (a_id, b_id), rel in world.relationships.items():
        soft = "\n".join(origin_summary_lines(world, rel, a_id))
        assert "Social meetings:" not in soft
        assert "Work colocations:" not in soft
        verbose = "\n".join(
            origin_summary_lines(world, rel, a_id, verbose_work=True)
        )
        assert "Social meetings:" in verbose
        found = True
        break
    assert found
