"""
Executor module - Dry-run and idempotent file operations.

Executes planned file operations with safety checks and dry-run support.
"""
import logging
import shutil
from pathlib import Path
from typing import List

from semantic_organizer.models import FileOperation

logger = logging.getLogger(__name__)


class Executor:
    """Executes file operations with dry-run and idempotent behavior."""

    def __init__(self, dry_run: bool = True):
        """
        Initialize executor.

        Args:
            dry_run: If True, simulate operations without actually moving files
        """
        self.dry_run = dry_run

    def execute_operation(self, operation: FileOperation) -> bool:
        """
        Execute a single file operation.

        Args:
            operation: Operation to execute

        Returns:
            True if operation succeeded, False otherwise
        """
        if operation.operation == "skip":
            logger.info(f"SKIP: {operation.source_path} - {operation.reason}")
            return True

        source = Path(operation.source_path)
        target = Path(operation.target_path)

        # Validate source exists
        if not source.exists():
            logger.error(f"Source file does not exist: {source}")
            return False

        # Check if already in target location (idempotent)
        if source == target:
            logger.info(f"ALREADY IN PLACE: {source}")
            return True

        if self.dry_run:
            logger.info(f"DRY-RUN {operation.operation.upper()}: {source} -> {target}")
            return True

        # Execute actual operation
        try:
            # Create target directory if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            if operation.operation == "move":
                logger.info(f"MOVING: {source} -> {target}")
                shutil.move(str(source), str(target))
                logger.info(f"Successfully moved file")
                return True
            elif operation.operation == "copy":
                logger.info(f"COPYING: {source} -> {target}")
                shutil.copy2(str(source), str(target))
                logger.info(f"Successfully copied file")
                return True
            else:
                logger.warning(f"Unknown operation: {operation.operation}")
                return False

        except Exception as e:
            logger.error(f"Failed to execute operation: {e}")
            return False

    def execute_operations(self, operations: List[FileOperation]) -> int:
        """
        Execute multiple file operations.

        Args:
            operations: List of operations to execute

        Returns:
            Number of successfully executed operations
        """
        if self.dry_run:
            logger.info("=" * 60)
            logger.info("DRY-RUN MODE - No files will be modified")
            logger.info("=" * 60)

        success_count = 0
        for i, operation in enumerate(operations, 1):
            logger.info(f"Operation {i}/{len(operations)}")
            if self.execute_operation(operation):
                success_count += 1

        logger.info(f"Executed {success_count}/{len(operations)} operations successfully")

        if self.dry_run:
            logger.info("=" * 60)
            logger.info("DRY-RUN COMPLETE - Run with dry_run=False to apply changes")
            logger.info("=" * 60)

        return success_count
