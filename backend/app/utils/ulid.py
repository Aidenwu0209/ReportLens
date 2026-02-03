"""T1 – ULID generator utility.

All primary keys follow the pattern ``{prefix}_{ulid}`` where *prefix* is a
short table-specific identifier (e.g. ``doc``, ``job``, ``ver``).
"""

from __future__ import annotations

from ulid import ULID


def generate_ulid(prefix: str) -> str:
    """Return a prefixed ULID string, e.g. ``doc_01HQXYZ...``."""
    return f"{prefix}_{ULID()}"


def generate_raw_ulid() -> str:
    """Return a raw ULID string without prefix."""
    return str(ULID())
