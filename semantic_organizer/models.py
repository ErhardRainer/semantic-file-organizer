"""
Core data models for semantic file organizer pipeline.

All models use Pydantic for validation and JSON schema generation.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class FileCategory(str, Enum):
    """File categories for semantic classification."""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    ARCHIVE = "archive"
    DATA = "data"
    UNKNOWN = "unknown"


class FileAnnotation(BaseModel):
    """LLM-generated annotation for a file."""
    file_path: str = Field(..., description="Original file path")
    category: FileCategory = Field(..., description="Semantic category")
    subcategory: Optional[str] = Field(None, description="More specific subcategory")
    description: str = Field(..., description="Brief description of the file")
    suggested_name: Optional[str] = Field(None, description="Suggested filename if renaming")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    tags: List[str] = Field(default_factory=list, description="Semantic tags")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Additional metadata")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v):
        """Ensure file_path is not empty."""
        if not v or not v.strip():
            raise ValueError("file_path cannot be empty")
        return v


class ScannedFile(BaseModel):
    """Metadata for a scanned file (read-only)."""
    path: str = Field(..., description="Absolute file path")
    name: str = Field(..., description="File name")
    extension: str = Field(..., description="File extension")
    size_bytes: int = Field(..., description="File size in bytes")
    modified_time: datetime = Field(..., description="Last modified timestamp")
    is_hidden: bool = Field(default=False, description="Whether file is hidden")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        """Ensure path is absolute."""
        if not Path(v).is_absolute():
            raise ValueError("Path must be absolute")
        return v


class OrganizationRule(BaseModel):
    """Decision rule for organizing files."""
    min_confidence: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")
    category_paths: Dict[FileCategory, str] = Field(
        ..., description="Target directory for each category"
    )
    preserve_structure: bool = Field(False, description="Preserve original subdirectory structure")
    allow_rename: bool = Field(False, description="Allow file renaming based on suggestions")


class FileOperation(BaseModel):
    """Planned file operation."""
    source_path: str = Field(..., description="Source file path")
    target_path: str = Field(..., description="Target file path")
    operation: str = Field(..., description="Operation type: move, copy, or skip")
    reason: str = Field(..., description="Reason for this operation")
    annotation: FileAnnotation = Field(..., description="Associated annotation")


class PipelineConfig(BaseModel):
    """Configuration for the entire pipeline."""
    source_directory: str = Field(..., description="Directory to scan")
    output_directory: str = Field(..., description="Base output directory for organized files")
    annotation_storage: str = Field("annotations.json", description="File to store annotations")
    rules: OrganizationRule = Field(default_factory=OrganizationRule, description="Organization rules")
    llm_model: str = Field("gpt-3.5-turbo", description="LLM model to use for annotation")
    dry_run: bool = Field(True, description="If True, only simulate operations")
    recursive: bool = Field(True, description="Scan directories recursively")
    exclude_patterns: List[str] = Field(
        default_factory=lambda: [".*", "__pycache__", "node_modules"],
        description="Patterns to exclude from scanning"
    )

    @field_validator('source_directory', 'output_directory')
    @classmethod
    def validate_directories(cls, v):
        """Ensure directories are absolute paths."""
        path = Path(v)
        if not path.is_absolute():
            raise ValueError("Directory paths must be absolute")
        return v


class PipelineResult(BaseModel):
    """Result of pipeline execution."""
    total_files_scanned: int = Field(0, description="Total files found")
    total_files_annotated: int = Field(0, description="Files successfully annotated")
    total_operations_planned: int = Field(0, description="Operations planned")
    total_operations_executed: int = Field(0, description="Operations executed")
    skipped_files: int = Field(0, description="Files skipped")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    operations: List[FileOperation] = Field(default_factory=list, description="All operations")
