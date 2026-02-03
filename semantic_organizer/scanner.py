"""
Scanner module - Read-only file system scanner.

Scans directories and collects file metadata without modifying anything.
"""
import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from semantic_organizer.models import ScannedFile

logger = logging.getLogger(__name__)


class Scanner:
    """Read-only file system scanner."""

    def __init__(self, exclude_patterns: List[str] = None):
        """
        Initialize scanner.

        Args:
            exclude_patterns: List of glob patterns to exclude from scanning
        """
        self.exclude_patterns = exclude_patterns or []

    def should_exclude(self, path: Path) -> bool:
        """
        Check if a path should be excluded based on patterns.

        Args:
            path: Path to check

        Returns:
            True if path should be excluded
        """
        name = path.name
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def scan_file(self, file_path: Path) -> ScannedFile:
        """
        Scan a single file and extract metadata.

        Args:
            file_path: Path to file

        Returns:
            ScannedFile with metadata
        """
        stat = file_path.stat()
        return ScannedFile(
            path=str(file_path.absolute()),
            name=file_path.name,
            extension=file_path.suffix,
            size_bytes=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            is_hidden=file_path.name.startswith(".")
        )

    def scan_directory(self, directory: Path, recursive: bool = True) -> List[ScannedFile]:
        """
        Scan a directory for files (read-only).

        Args:
            directory: Directory to scan
            recursive: If True, scan subdirectories recursively

        Returns:
            List of ScannedFile objects

        Raises:
            ValueError: If directory doesn't exist or is not a directory
        """
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        scanned_files = []
        pattern = "**/*" if recursive else "*"

        logger.info(f"Scanning directory: {directory} (recursive={recursive})")

        try:
            for path in directory.glob(pattern):
                # Skip directories
                if path.is_dir():
                    continue

                # Skip excluded patterns
                if self.should_exclude(path):
                    logger.debug(f"Excluding file: {path}")
                    continue

                try:
                    scanned_file = self.scan_file(path)
                    scanned_files.append(scanned_file)
                    logger.debug(f"Scanned file: {path}")
                except Exception as e:
                    logger.warning(f"Failed to scan file {path}: {e}")

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            raise

        logger.info(f"Scanned {len(scanned_files)} files from {directory}")
        return scanned_files
