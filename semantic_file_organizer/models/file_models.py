from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class FileRecord:
    path: Path
    filename: str
    size: Optional[int] = None
    modified_date: Optional[datetime] = None


@dataclass(frozen=True)
class SemanticAnnotation:
    category: str
    series: Optional[str] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    track: Optional[int] = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class ActionType(str, Enum):
    MOVE = "MOVE"
    SKIP = "SKIP"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class PlannedAction:
    source_path: Path
    target_path: Path
    action_type: ActionType
    reason: str
