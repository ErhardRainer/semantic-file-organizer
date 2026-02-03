"""
Dataset storage module - Persist and load annotations.

Stores annotation data in JSON format for reproducibility and auditing.
"""
import json
import logging
from pathlib import Path
from typing import List

from semantic_organizer.models import FileAnnotation

logger = logging.getLogger(__name__)


class DatasetStorage:
    """Storage for file annotations."""

    def __init__(self, storage_path: str):
        """
        Initialize storage.

        Args:
            storage_path: Path to JSON file for storing annotations
        """
        self.storage_path = Path(storage_path)

    def save_annotations(self, annotations: List[FileAnnotation]) -> None:
        """
        Save annotations to JSON file.

        Args:
            annotations: List of annotations to save

        Raises:
            Exception: If save fails
        """
        logger.info(f"Saving {len(annotations)} annotations to {self.storage_path}")

        try:
            # Ensure parent directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to JSON-serializable format
            data = {
                "version": "1.0",
                "count": len(annotations),
                "annotations": [annotation.model_dump(mode='json') for annotation in annotations]
            }

            # Write to file with pretty formatting
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Successfully saved annotations to {self.storage_path}")

        except Exception as e:
            logger.error(f"Failed to save annotations: {e}")
            raise

    def load_annotations(self) -> List[FileAnnotation]:
        """
        Load annotations from JSON file.

        Returns:
            List of FileAnnotations

        Raises:
            FileNotFoundError: If storage file doesn't exist
            Exception: If load fails
        """
        if not self.storage_path.exists():
            raise FileNotFoundError(f"Annotation file not found: {self.storage_path}")

        logger.info(f"Loading annotations from {self.storage_path}")

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            annotations = [
                FileAnnotation(**annotation_data)
                for annotation_data in data["annotations"]
            ]

            logger.info(f"Successfully loaded {len(annotations)} annotations")
            return annotations

        except Exception as e:
            logger.error(f"Failed to load annotations: {e}")
            raise

    def exists(self) -> bool:
        """
        Check if storage file exists.

        Returns:
            True if file exists
        """
        return self.storage_path.exists()
