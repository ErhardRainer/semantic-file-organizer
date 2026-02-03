from __future__ import annotations

import logging

from semantic_file_organizer.models import PlannedAction

logger = logging.getLogger(__name__)


def execute(action: PlannedAction, dry_run: bool = True) -> None:
    """
    Log intended action without modifying the filesystem.
    """
    logger.info(
        "[DRY-RUN=%s] %s: %s -> %s | reason=%s",
        dry_run,
        action.action_type.value,
        action.source_path,
        action.target_path,
        action.reason,
    )
    # No filesystem operations executed.
