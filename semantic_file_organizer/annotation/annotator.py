from __future__ import annotations

import logging
from typing import Any

from semantic_file_organizer.models import SemanticAnnotation, FileRecord

logger = logging.getLogger(__name__)


def annotate(file_record: FileRecord) -> SemanticAnnotation:
    """
    Placeholder annotation that returns deterministic mocked annotation.
    """
    # Simple deterministic mock based on filename
    category = "unknown"
    confidence = 0.5
    if file_record.filename.lower().endswith((".mp4", ".mkv", ".avi")):
        category = "video"
        confidence = 0.92
    elif file_record.filename.lower().endswith((".mp3", ".flac", ".wav")):
        category = "audio"
        confidence = 0.88
    annotation = SemanticAnnotation(category=category, confidence=confidence)
    logger.info("Annotated %s as %s (%.2f)", file_record.filename, category, confidence)
    return annotation
