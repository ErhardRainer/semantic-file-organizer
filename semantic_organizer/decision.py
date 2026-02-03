"""
Decision rules module - Confidence-based filtering and decision logic.

Applies deterministic rules to determine which files should be organized.
"""
import logging
from typing import List, Tuple

from semantic_organizer.models import FileAnnotation, OrganizationRule

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Confidence-based decision engine for file organization."""

    def __init__(self, rules: OrganizationRule):
        """
        Initialize decision engine.

        Args:
            rules: Organization rules to apply
        """
        self.rules = rules

    def should_organize(self, annotation: FileAnnotation) -> Tuple[bool, str]:
        """
        Decide if a file should be organized based on rules.

        Args:
            annotation: File annotation

        Returns:
            Tuple of (should_organize: bool, reason: str)
        """
        # Check confidence threshold
        if annotation.confidence < self.rules.min_confidence:
            reason = f"Confidence {annotation.confidence:.2f} below threshold {self.rules.min_confidence:.2f}"
            logger.debug(f"Skipping {annotation.file_path}: {reason}")
            return False, reason

        # Check if category has a target path
        if annotation.category not in self.rules.category_paths:
            reason = f"No target path defined for category {annotation.category}"
            logger.debug(f"Skipping {annotation.file_path}: {reason}")
            return False, reason

        reason = f"Confidence {annotation.confidence:.2f} meets threshold, category has target path"
        return True, reason

    def filter_annotations(
        self, annotations: List[FileAnnotation]
    ) -> Tuple[List[FileAnnotation], List[FileAnnotation]]:
        """
        Filter annotations based on decision rules.

        Args:
            annotations: List of annotations to filter

        Returns:
            Tuple of (approved_annotations, rejected_annotations)
        """
        approved = []
        rejected = []

        for annotation in annotations:
            should_org, reason = self.should_organize(annotation)
            if should_org:
                approved.append(annotation)
                logger.info(f"Approved for organization: {annotation.file_path} - {reason}")
            else:
                rejected.append(annotation)
                logger.info(f"Rejected: {annotation.file_path} - {reason}")

        logger.info(f"Decision results: {len(approved)} approved, {len(rejected)} rejected")
        return approved, rejected
