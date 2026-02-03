"""
Scanner module - Read-only file system scanner.

Scans directories and collects file metadata without modifying anything.
Includes optional JSON export for PowerShell-parity scanning.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from semantic_organizer.models import ScannedFile

logger = logging.getLogger(__name__)


def compute_md5(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute MD5 checksum of a file without loading it fully into memory.
    """
    md5 = hashlib.md5()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            md5.update(chunk)
    return md5.hexdigest()


def build_output_filename(prefix: str = "files") -> str:
    """
    Build a filesystem-safe timestamped filename.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.json"


class Scanner:
    """Read-only file system scanner."""

    def __init__(self, exclude_patterns: Optional[List[str]] = None):
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

    def _iter_paths(self, directory: Path, recursive: bool) -> Iterable[Path]:
        """
        Yield file paths in a deterministic order.
        """
        paths = directory.rglob("*") if recursive else directory.glob("*")
        for path in sorted(paths, key=lambda item: item.as_posix().lower()):
            if path.is_dir():
                continue
            if self.should_exclude(path):
                logger.debug("Excluding file: %s", path)
                continue
            yield path

    def scan_file(self, file_path: Path, calculate_checksum: bool = False) -> ScannedFile:
        """
        Scan a single file and extract metadata.

        Args:
            file_path: Path to file
            calculate_checksum: If True, compute MD5 checksum

        Returns:
            ScannedFile with metadata
        """
        stat = file_path.stat()
        checksum = compute_md5(file_path) if calculate_checksum else None
        return ScannedFile(
            path=str(file_path.absolute()),
            name=file_path.name,
            extension=file_path.suffix,
            size_bytes=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            is_hidden=file_path.name.startswith("."),
            checksum=checksum,
        )

    def scan_directory(
        self,
        directory: Path,
        recursive: bool = True,
        calculate_checksum: bool = False,
    ) -> List[ScannedFile]:
        """
        Scan a directory for files (read-only).

        Args:
            directory: Directory to scan
            recursive: If True, scan subdirectories recursively
            calculate_checksum: If True, compute MD5 checksums

        Returns:
            List of ScannedFile objects

        Raises:
            ValueError: If directory doesn't exist or is not a directory
        """
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        scanned_files: List[ScannedFile] = []

        logger.info("Scanning directory: %s (recursive=%s)", directory, recursive)

        try:
            for path in self._iter_paths(directory, recursive):
                try:
                    scanned_file = self.scan_file(path, calculate_checksum=calculate_checksum)
                    scanned_files.append(scanned_file)
                    logger.debug("Scanned file: %s", path)
                except Exception as exc:
                    logger.warning("Failed to scan file %s: %s", path, exc)

        except Exception as exc:
            logger.error("Error scanning directory %s: %s", directory, exc)
            raise

        logger.info("Scanned %s files from %s", len(scanned_files), directory)
        return scanned_files


def scan_directory_records(
    root_dir: Path,
    recursive: bool = True,
    calculate_checksum: bool = False,
    exclude_patterns: Optional[List[str]] = None,
) -> List[dict]:
    """
    Scan a directory and return PowerShell-parity JSON records.
    """
    root_dir = root_dir.resolve()
    scanner = Scanner(exclude_patterns=exclude_patterns)
    scanned_files = scanner.scan_directory(
        root_dir,
        recursive=recursive,
        calculate_checksum=calculate_checksum,
    )

    records: List[dict] = []
    for scanned in scanned_files:
        file_path = Path(scanned.path)
        relative_path = file_path.relative_to(root_dir)
        relative_parent = relative_path.parent
        relative_dir = "" if relative_parent == Path(".") else str(relative_parent)

        record = {
            "path": relative_dir,
            "filename": relative_path.name,
            "complete_path": str(relative_path),
            "checksum": scanned.checksum if calculate_checksum and scanned.checksum else "",
            "size": scanned.size_bytes,
            "date": scanned.modified_time.strftime("%Y-%m-%d"),
        }
        records.append(record)

    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively scan a directory and export file metadata to JSON."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Root directory to scan",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where JSON output will be written",
    )

    parser.add_argument(
        "--checksum",
        action="store_true",
        help="Enable MD5 checksum calculation (default: disabled)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive scanning",
    )

    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob pattern to exclude (repeatable)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    root_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    recursive = not args.no_recursive

    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {root_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    records = scan_directory_records(
        root_dir=root_dir,
        recursive=recursive,
        calculate_checksum=args.checksum,
        exclude_patterns=args.exclude,
    )

    output_file = output_dir / build_output_filename()

    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)

    print(f"Scanned files : {len(records)}")
    print(f"Output written: {output_file}")


if __name__ == "__main__":
    main()
