from __future__ import annotations
from collections import deque
from typing import Deque, Generic, TypeVar, List

T = TypeVar("T")

class RingBuffer(Generic[T]):
    def __init__(self, maxlen: int):
        self.buf: Deque[T] = deque(maxlen=maxlen)

    def append(self, x: T) -> None:
        self.buf.append(x)

    def __len__(self) -> int:
        return len(self.buf)

    def values(self) -> List[T]:
        return list(self.buf)

    def last(self) -> T | None:
        return self.buf[-1] if self.buf else None
