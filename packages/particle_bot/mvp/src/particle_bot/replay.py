from __future__ import annotations
from typing import Iterable, List, Dict, Any
from particle_bot.types import BaseEvent, EventType, Symbol
from particle_bot.event_bus import EventBus

def replay(events: Iterable[BaseEvent], bus: EventBus) -> None:
    for ev in events:
        bus.publish(ev)
