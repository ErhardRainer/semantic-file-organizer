"""
Annotation module - LLM-based semantic classification.

Uses LLM to classify files semantically, returning structured JSON.
LLM performs NO file operations, only classification.
"""
import json
import logging
from typing import List, Optional

from openai import OpenAI

from semantic_organizer.models import FileAnnotation, FileCategory, ScannedFile

logger = logging.getLogger(__name__)


class Annotator:
    """LLM-based file annotator that returns structured JSON."""

    SYSTEM_PROMPT = """You are a file classification assistant. Your ONLY job is to analyze file paths and names to semantically classify them. You must NEVER perform file operations.

Return ONLY valid JSON in the following format:
{
  "category": "one of: document, image, video, audio, code, archive, data, unknown",
  "subcategory": "optional more specific category",
  "description": "brief description of what the file likely contains",
  "suggested_name": "optional better filename if current one is poor",
  "confidence": 0.0-1.0,
  "tags": ["tag1", "tag2"],
  "metadata": {"key": "value"}
}

Rules:
- Return ONLY the JSON object, no other text
- confidence should be 0.0-1.0 based on how certain you are
- Use existing filename patterns and extensions to guide classification
- Be conservative with confidence - use lower values when uncertain
"""

    def __init__(self, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None):
        """
        Initialize annotator.

        Args:
            model: OpenAI model to use
            api_key: OpenAI API key (uses env var OPENAI_API_KEY if None)
        """
        self.model = model
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()

    def _create_user_prompt(self, scanned_file: ScannedFile) -> str:
        """
        Create prompt for file classification.

        Args:
            scanned_file: File to classify

        Returns:
            Prompt string
        """
        return f"""Classify this file:
Path: {scanned_file.path}
Name: {scanned_file.name}
Extension: {scanned_file.extension}
Size: {scanned_file.size_bytes} bytes
Modified: {scanned_file.modified_time}
"""

    def annotate_file(self, scanned_file: ScannedFile) -> FileAnnotation:
        """
        Annotate a single file using LLM.

        Args:
            scanned_file: Scanned file to annotate

        Returns:
            FileAnnotation with LLM classification

        Raises:
            Exception: If LLM call fails or returns invalid JSON
        """
        logger.debug(f"Annotating file: {scanned_file.path}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": self._create_user_prompt(scanned_file)}
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=500
            )

            # Extract JSON from response
            content = response.choices[0].message.content.strip()
            logger.debug(f"LLM response: {content}")

            # Parse JSON
            annotation_data = json.loads(content)

            # Create FileAnnotation with validated data
            annotation = FileAnnotation(
                file_path=scanned_file.path,
                category=FileCategory(annotation_data["category"]),
                subcategory=annotation_data.get("subcategory"),
                description=annotation_data["description"],
                suggested_name=annotation_data.get("suggested_name"),
                confidence=float(annotation_data["confidence"]),
                tags=annotation_data.get("tags", []),
                metadata=annotation_data.get("metadata", {})
            )

            logger.info(f"Annotated {scanned_file.name}: {annotation.category} (confidence: {annotation.confidence:.2f})")
            return annotation

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"LLM returned invalid JSON for {scanned_file.path}") from e
        except Exception as e:
            logger.error(f"Failed to annotate file {scanned_file.path}: {e}")
            raise

    def annotate_files(self, scanned_files: List[ScannedFile]) -> List[FileAnnotation]:
        """
        Annotate multiple files.

        Args:
            scanned_files: List of files to annotate

        Returns:
            List of FileAnnotations
        """
        annotations = []
        for scanned_file in scanned_files:
            try:
                annotation = self.annotate_file(scanned_file)
                annotations.append(annotation)
            except Exception as e:
                logger.warning(f"Skipping file due to annotation error: {scanned_file.path}: {e}")
                continue

        logger.info(f"Successfully annotated {len(annotations)}/{len(scanned_files)} files")
        return annotations
