from __future__ import annotations

from semantic_file_organizer.models import ActionType, SemanticAnnotation


def decide(annotation: SemanticAnnotation) -> ActionType:
    if annotation.confidence >= 0.9:
        return ActionType.MOVE
    if 0.75 <= annotation.confidence < 0.9:
        return ActionType.REVIEW
    return ActionType.SKIP
