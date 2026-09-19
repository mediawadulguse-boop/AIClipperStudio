from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ClipCandidate:
    start: float
    end: float
    score: int
    title: str
    reason: str
    transcript: str
    hook: int = 0
    curiosity: int = 0
    conflict: int = 0
    information: int = 0
    emotion: int = 0
    standalone: int = 0
    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
