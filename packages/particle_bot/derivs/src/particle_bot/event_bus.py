from __future__ import annotations
from typing import Callable, Dict, List, Type
from particle_bot.types import BaseEvent, EventType

Handler = Callable[[BaseEvent], None]

class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[EventType, List[Handler]] = {}

    def subscribe(self, etype: EventType, handler: Handler) -> None:
        self._subs.setdefault(etype, []).append(handler)

    def publish(self, ev: BaseEvent) -> None:
        for h in self._subs.get(ev.etype, []):
            h(ev)
