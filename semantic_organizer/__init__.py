"""Package initialization."""
__version__ = "0.1.0"

from semantic_organizer.models import (
    FileAnnotation,
    FileCategory,
    FileOperation,
    OrganizationRule,
    PipelineConfig,
    PipelineResult,
    ScannedFile,
)

__all__ = [
    "FileAnnotation",
    "FileCategory",
    "FileOperation",
    "OrganizationRule",
    "PipelineConfig",
    "PipelineResult",
    "ScannedFile",
]
