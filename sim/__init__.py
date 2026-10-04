"""Headless simulation core for SitSimCity.

No pygame imports belong in this package.
"""

from sim.world import World, create_world

__all__ = ["World", "create_world"]
