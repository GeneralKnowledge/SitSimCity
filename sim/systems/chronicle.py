"""M9: seeded chronicle phrases — DF-flavored prose, not audit logs."""

from __future__ import annotations

import random
from typing import Mapping

# Variant tables. Placeholders use str.format kwargs (name, place, old, new, …).
PHRASES: dict[str, tuple[str, ...]] = {
    # Day-1 placement
    "settled_home": (
        "Settled at {place}",
        "Made a home at {place}",
        "Took rooms at {place}",
    ),
    "started_job": (
        "Took a post at {place}",
        "Started work at {place}",
        "Joined {place}",
    ),
    # Circumstances — life events (no day-count parentheticals)
    "became_sick": (
        "Took to bed; the house went quiet",
        "Came down with something and cancelled the week",
        "Fell ill and kept to the house",
    ),
    "recovered": (
        "Was back on their feet",
        "The illness finally let go",
        "Felt well enough to face the town again",
    ),
    "became_unemployed": (
        "Walked out of {place} for the last time",
        "Left {place} without another shift to go to",
        "Finished at {place} and found the days suddenly empty",
    ),
    "job_changed": (
        "Started at {new} after leaving {old}",
        "Took up work at {new}, leaving {old} behind",
        "Traded {old} for a desk at {new}",
    ),
    "became_overworked": (
        "The job ate the evenings",
        "Work stretched late and left little else",
        "Came home too tired to be anyone's company",
    ),
    "overwork_ended": (
        "The pressure at work let up",
        "The long days finally eased",
        "Found evenings again after the rush",
    ),
    "moved_home": (
        "Packed up at {old}; keys now for {new}",
        "Left {old} behind for {new}",
        "Moved house from {old} to {new}",
    ),
    # Circumstance inspector notes (short)
    "note_sick": ("resting at home", "laid up indoors"),
    "note_unemployed": ("between posts after {place}", "looking past {place}"),
    "note_overworked": ("the job is eating the evenings", "long days at work"),
    "note_moved": ("new keys after {place}", "still unpacking from {place}"),
    # Contact story notes on bonds
    "contact_ill": (
        "Scarce while laid up — friends noticed the empty stool",
        "Hard to find while under the weather",
        "Kept to bed; old haunts went without them",
    ),
    "contact_left_work": (
        "Harder to catch after leaving work",
        "No longer in the old corridors",
        "Drifted from the workday crowd",
    ),
    "contact_moved": (
        "Harder to find after the move across town",
        "New streets, old habits slower to follow",
        "The move put distance in the usual routes",
    ),
    "contact_job_change": (
        "No longer crossing paths in the corridors",
        "Fewer shared workdays after the job change",
        "The new workplace pulled the schedule askew",
    ),
    # Bond milestones
    "first_met_work": (
        "Fell into the same corridor at work",
        "First crossed paths at work",
    ),
    "first_met_pub": (
        "Fell into conversation at the pub",
        "Shared a quiet drink and a few words at the pub",
    ),
    "first_met_cafe": (
        "Struck up talk over cups at the cafe",
        "First met over coffee at the cafe",
    ),
    "first_met_shop": (
        "Bumped into each other at the shop",
        "Exchanged nods at the shop",
    ),
    "first_met_visit": (
        "First met during a visit",
        "A household visit put them in the same room",
    ),
    "first_met_other": (
        "Crossed paths around town",
        "Met by chance around town",
    ),
    "became_close_work": (
        "Grew close despite the workplace noise",
        "Found a friendship between shifts",
    ),
    "became_close_pub": (
        "Grew close over nights at the pub",
        "The pub turned acquaintances into friends",
    ),
    "became_close_cafe": (
        "Grew close over cafe mornings",
        "Familiar faces at the cafe became friendship",
    ),
    "became_close_shop": (
        "Grew close in the shop aisles",
        "Errands turned into something friendlier",
    ),
    "became_close_visit": (
        "A visit stretched into something like friendship",
        "Grew close over quiet visits",
    ),
    "became_close_other": (
        "Grew close around town",
        "Town errands turned into friendship",
    ),
    "became_close_with": (
        "Grew close to {name}",
        "Found a friend in {name}",
        "Became one of {name}'s people",
    ),
    "reunited_work": ("Crossed paths again at work",),
    "reunited_pub": (
        "Crossed paths again at the pub",
        "Found each other again at the pub",
    ),
    "reunited_cafe": (
        "Crossed paths again at the cafe",
        "The cafe brought them back together",
    ),
    "reunited_shop": ("Crossed paths again at the shop",),
    "reunited_visit": (
        "A visit brought them together again",
        "Found each other again on a visit",
    ),
    "reunited_other": ("Crossed paths again around town",),
    "reunited_with": (
        "Found {name} again",
        "Crossed paths with {name} once more",
    ),
    "cooling": (
        "They have been missing each other lately",
        "The friendship has been cooling",
        "Days pass without the usual meeting",
    ),
    # Plan notes (soft agenda)
    "plan_straight_home": (
        "Home again when the day ended",
        "Straight home when work let out",
    ),
    "plan_long_day_home": (
        "Too tired for anything but home",
        "Long day — home and nothing more",
    ),
    "plan_evening_shift": ("On the evening shift", "Evening shift"),
    "plan_between_jobs": ("Looking for work", "Between jobs"),
    "plan_home_sick": ("Home sick", "Keeping to bed"),
    "plan_settling": (
        "Settling into the new neighbourhood",
        "Still learning the new streets",
    ),
}


def pick_phrase(rng: random.Random, key: str, **fmt: object) -> str:
    """Choose a seeded variant and format placeholders."""
    variants = PHRASES.get(key)
    if not variants:
        raise KeyError(f"Unknown chronicle phrase key: {key}")
    template = rng.choice(variants)
    if fmt:
        return template.format(**fmt)
    return template


def first_met_key(context: str | None) -> str:
    if context in {"work", "pub", "cafe", "shop", "visit"}:
        return f"first_met_{context}"
    return "first_met_other"


def became_close_key(context: str | None) -> str:
    if context in {"work", "pub", "cafe", "shop", "visit"}:
        return f"became_close_{context}"
    return "became_close_other"


def reunited_key(context: str | None) -> str:
    if context in {"work", "pub", "cafe", "shop", "visit"}:
        return f"reunited_{context}"
    return "reunited_other"


def relative_day_phrase(event_day: int, current_day: int) -> str:
    """Human gap wording for recent events."""
    gap = current_day - event_day
    if gap <= 0:
        return "today"
    if gap == 1:
        return "yesterday"
    return f"{gap} days ago"


def time_of_day_band(minute_of_day: int) -> str:
    hour = minute_of_day // 60
    if hour < 6:
        return "night"
    if hour < 11:
        return "morning"
    if hour < 14:
        return "midday"
    if hour < 17:
        return "afternoon"
    if hour < 21:
        return "evening"
    return "night"


def smart_truncate(text: str, max_chars: int) -> str:
    """Truncate at a word boundary when possible."""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return "…"
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ·,;:") + "…"


def street_label(building_name: str) -> str:
    """Home map label: street token, not house number."""
    parts = building_name.split()
    if len(parts) >= 2 and parts[0].isdigit():
        # "1 Maple Avenue" -> "Maple"
        return parts[1]
    return parts[0] if parts else building_name


def format_mapping(mapping: Mapping[str, object]) -> dict[str, object]:
    return dict(mapping)
