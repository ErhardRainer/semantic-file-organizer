from __future__ import annotations

import logging
from pathlib import Path

from semantic_file_organizer.models import ActionType, PlannedAction, SemanticAnnotation, FileRecord
from semantic_file_organizer.decision.decision import decide

logger = logging.getLogger(__name__)


def compute_target_path(file_record: FileRecord, annotation: SemanticAnnotation) -> Path:
    base = file_record.path.parent
    category_folder = annotation.category or "uncategorized"
    return base / category_folder / file_record.filename


def plan_action(file_record: FileRecord, annotation: SemanticAnnotation) -> PlannedAction:
    action_type = decide(annotation)
    target_path = compute_target_path(file_record, annotation)
    reason = f"Confidence {annotation.confidence:.2f} leads to {action_type.value}"
    logger.info("Planned %s -> %s (%s)", file_record.path, target_path, action_type.value)
    return PlannedAction(
        source_path=file_record.path,
        target_path=target_path,
        action_type=action_type,
        reason=reason,
    )
