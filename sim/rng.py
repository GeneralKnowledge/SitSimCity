from __future__ import annotations

import random


def make_rng(seed: int, stream: str = "world") -> random.Random:
    """Deterministic RNG derived from a master seed and named stream."""
    # Stable mixing; avoids callers accidentally sharing one global Random.
    mixed = (seed ^ (zlib_crc32(stream) << 1)) & 0xFFFFFFFFFFFFFFFF
    return random.Random(mixed)


def zlib_crc32(text: str) -> int:
    import zlib

    return zlib.crc32(text.encode("utf-8")) & 0xFFFFFFFF
