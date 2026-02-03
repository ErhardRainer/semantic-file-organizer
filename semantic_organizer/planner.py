"""
Planner module - Compute target paths for file organization.

Determines where files should be moved based on annotations and rules.
"""
import logging
from pathlib import Path
from typing import List

from semantic_organizer.models import FileAnnotation, FileOperation, OrganizationRule

logger = logging.getLogger(__name__)


class Planner:
    """Computes target paths for file organization."""

    def __init__(self, output_directory: str, rules: OrganizationRule):
        """
        Initialize planner.

        Args:
            output_directory: Base output directory for organized files
            rules: Organization rules
        """
        self.output_directory = Path(output_directory)
        self.rules = rules

    def compute_target_path(self, annotation: FileAnnotation) -> str:
        """
        Compute target path for a file.

        Args:
            annotation: File annotation

        Returns:
            Target path as string
        """
        source_path = Path(annotation.file_path)

        # Get category target directory
        category_dir = self.rules.category_paths.get(annotation.category)
        if not category_dir:
            raise ValueError(f"No target path for category {annotation.category}")

        target_dir = self.output_directory / category_dir

        # Add subcategory if present
        if annotation.subcategory:
            target_dir = target_dir / annotation.subcategory

        # Determine filename
        if self.rules.allow_rename and annotation.suggested_name:
            # Use suggested name, but keep original extension if new name doesn't have one
            suggested = Path(annotation.suggested_name)
            if not suggested.suffix and source_path.suffix:
                filename = suggested.stem + source_path.suffix
            else:
                filename = annotation.suggested_name
        else:
            filename = source_path.name

        # Construct full target path
        target_path = target_dir / filename

        # Handle name collisions by adding suffix
        if target_path.exists() and target_path != source_path:
            base = target_path.stem
            ext = target_path.suffix
            counter = 1
            while target_path.exists():
                filename = f"{base}_{counter}{ext}"
                target_path = target_dir / filename
                counter += 1

        return str(target_path)

    def plan_operation(self, annotation: FileAnnotation) -> FileOperation:
        """
        Plan a single file operation.

        Args:
            annotation: File annotation

        Returns:
            FileOperation describing what to do
        """
        source_path = annotation.file_path
        target_path = self.compute_target_path(annotation)

        # Determine operation type
        if source_path == target_path:
            operation = "skip"
            reason = "Source and target paths are identical"
        else:
            operation = "move"
            reason = f"Organize {annotation.category} file to {Path(target_path).parent}"

        logger.debug(f"Planned operation: {operation} {source_path} -> {target_path}")

        return FileOperation(
            source_path=source_path,
            target_path=target_path,
            operation=operation,
            reason=reason,
            annotation=annotation
        )

    def plan_operations(self, annotations: List[FileAnnotation]) -> List[FileOperation]:
        """
        Plan operations for multiple files.

        Args:
            annotations: List of approved annotations

        Returns:
            List of planned operations
        """
        operations = []

        for annotation in annotations:
            try:
                operation = self.plan_operation(annotation)
                operations.append(operation)
            except Exception as e:
                logger.error(f"Failed to plan operation for {annotation.file_path}: {e}")
                # Create a skip operation for files we can't plan
                operations.append(FileOperation(
                    source_path=annotation.file_path,
                    target_path=annotation.file_path,
                    operation="skip",
                    reason=f"Planning failed: {e}",
                    annotation=annotation
                ))

        logger.info(f"Planned {len(operations)} operations")

        # Log operation summary
        move_count = sum(1 for op in operations if op.operation == "move")
        skip_count = sum(1 for op in operations if op.operation == "skip")
        logger.info(f"Operations: {move_count} moves, {skip_count} skips")

        return operations
