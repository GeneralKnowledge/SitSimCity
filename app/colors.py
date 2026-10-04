from __future__ import annotations

from sim.types import Activity, BuildingKind

BG = (28, 32, 38)
EMPTY = (46, 56, 48)
ROAD = (70, 74, 82)
PANEL = (18, 20, 24)
PANEL_BORDER = (90, 96, 108)
TEXT = (230, 232, 236)
MUTED = (160, 166, 176)
SELECT = (255, 220, 90)
FOLLOW = (120, 220, 160)
DAY_CUE = (210, 218, 190)
DAY_CUE_DIM = (40, 48, 42)

BUILDING_FILL = {
    BuildingKind.HOME: (120, 92, 72),
    BuildingKind.WORKPLACE: (70, 110, 150),
    BuildingKind.PUB: (140, 80, 110),
    BuildingKind.SHOP: (90, 130, 90),
    BuildingKind.CAFE: (150, 120, 70),
    BuildingKind.POLICE: (60, 80, 140),
    BuildingKind.HOSPITAL: (160, 90, 90),
}

PERSON_BY_ACTIVITY = {
    Activity.SLEEP: (180, 180, 190),
    Activity.AT_HOME: (200, 190, 170),
    Activity.TRAVEL: (240, 210, 80),
    Activity.WORK: (100, 170, 220),
    Activity.WAIT: (200, 200, 120),
    Activity.AT_CAFE: (230, 170, 90),
    Activity.AT_SHOP: (130, 200, 130),
    Activity.AT_PUB: (220, 120, 170),
    Activity.VISITING: (180, 140, 230),
}
