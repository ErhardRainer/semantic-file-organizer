from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from semantic_file_organizer.models import FileRecord

logger = logging.getLogger(__name__)


def scan_directory(root: Path, dry_run: bool = True) -> List[FileRecord]:
    """
    Recursively collect file paths under root without modifying the filesystem.
    """
    root = root.expanduser().resolve()
    records: List[FileRecord] = []
    for path in root.rglob("*"):
        if path.is_file():
            stat = path.stat()
            records.append(
                FileRecord(
                    path=path,
                    filename=path.name,
                    size=stat.st_size,
                    modified_date=None,
                )
            )
            logger.info("Scanned file: %s", path)
    logger.info("Dry-run mode: %s. Total files: %s", dry_run, len(records))
    return records
