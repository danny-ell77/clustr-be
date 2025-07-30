"""
Event models package for core.common.
"""

from core.common.models.event.event import (
    Event,
)
from core.common.models.event.event_guest import (
    EventGuest,
)

__all__ = [
    "Event",
    "EventGuest",
]