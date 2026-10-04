from __future__ import annotations

from sim.types import Activity, Person, ScheduleEntry


def build_daily_commute_schedule(person: Person) -> list[ScheduleEntry]:
    """Milestone 3 schedule: sleep at home, work, sleep at home."""
    leave_home = 7 * 60 + 20 + person.wake_offset_minutes  # ~07:20–08:00
    leave_work = 17 * 60 + (person.wake_offset_minutes % 25)  # staggered exit
    return [
        ScheduleEntry(0, Activity.SLEEP, person.home_id),
        ScheduleEntry(leave_home, Activity.WORK, person.work_id),
        ScheduleEntry(leave_work, Activity.SLEEP, person.home_id),
    ]


def assign_schedules(people: dict[int, Person]) -> None:
    for person in people.values():
        person.schedule = build_daily_commute_schedule(person)


def active_goal(person: Person, minute_of_day: int) -> ScheduleEntry | None:
    """Latest schedule entry whose start time has been reached today."""
    current: ScheduleEntry | None = None
    for entry in person.schedule:
        if entry.minute_of_day <= minute_of_day:
            current = entry
        else:
            break
    return current
