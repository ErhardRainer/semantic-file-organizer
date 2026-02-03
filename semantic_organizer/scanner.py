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
import os
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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


def json_pretty_item(obj: Dict[str, Any], base_indent: int = 2) -> str:
    """
    Serialize a dict as pretty JSON and indent it for embedding into a JSON array.
    """
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    pad = " " * base_indent
    return "\n".join(pad + line for line in text.splitlines())


def _handle_error(policy: str, message: str, exc: Optional[BaseException] = None) -> None:
    """
    Handle errors based on policy.

    policy: "fail" or "skip"
    """
    if policy == "fail":
        if exc is not None:
            raise RuntimeError(message) from exc
        raise RuntimeError(message)

    if exc is not None:
        logger.warning("%s: %s", message, exc)
    else:
        logger.warning("%s", message)


class Scanner:
    """Read-only file system scanner."""

    def __init__(self, exclude_patterns: Optional[List[str]] = None):
        """
        Initialize scanner.

        Args:
            exclude_patterns: List of glob patterns to exclude from scanning
        """
        self.exclude_patterns = exclude_patterns or []

    def should_exclude(self, relative_path: Path) -> bool:
        """
        Check if a relative path should be excluded based on patterns.

        Args:
            relative_path: Relative path from the scan root

        Returns:
            True if path should be excluded
        """
        if not self.exclude_patterns:
            return False

        for part in relative_path.parts:
            for pattern in self.exclude_patterns:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False

    def _iter_file_entries(
        self,
        directory: Path,
        recursive: bool,
        follow_symlinks: bool = False,
        on_error: str = "skip",
    ) -> Iterable[Tuple[Path, Path, os.stat_result]]:
        """
        Yield (absolute_path, relative_path, stat) tuples in deterministic order.
        """
        root_dir = directory.resolve()
        yield from self._walk_directory(root_dir, Path(), recursive, follow_symlinks, on_error)

    def _walk_directory(
        self,
        directory: Path,
        relative_dir: Path,
        recursive: bool,
        follow_symlinks: bool,
        on_error: str,
    ) -> Iterable[Tuple[Path, Path, os.stat_result]]:
        try:
            with os.scandir(directory) as iterator:
                directories = []
                files = []
                for entry in iterator:
                    relative_path = relative_dir / entry.name
                    if self.should_exclude(relative_path):
                        logger.debug("Excluding path: %s", relative_path)
                        continue
                    try:
                        is_dir = entry.is_dir(follow_symlinks=follow_symlinks)
                    except OSError as exc:
                        _handle_error(on_error, f"Failed to access {entry.path}", exc)
                        continue
                    if is_dir:
                        directories.append((entry.name, entry, relative_path))
                    else:
                        files.append((entry.name, entry, relative_path))
        except OSError as exc:
            _handle_error(on_error, f"Failed to list directory {directory}", exc)
            return

        for _, entry, relative_path in sorted(files, key=lambda item: item[0]):
            try:
                stat = entry.stat(follow_symlinks=follow_symlinks)
            except OSError as exc:
                _handle_error(on_error, f"Failed to stat file {entry.path}", exc)
                continue

            yield Path(entry.path), relative_path, stat

        if recursive:
            for _, entry, relative_path in sorted(directories, key=lambda item: item[0]):
                yield from self._walk_directory(
                    Path(entry.path),
                    relative_path,
                    recursive,
                    follow_symlinks,
                    on_error,
                )

    def scan_file(
        self,
        file_path: Path,
        calculate_checksum: bool = False,
        stat: Optional[os.stat_result] = None,
    ) -> ScannedFile:
        """
        Scan a single file and extract metadata.

        Args:
            file_path: Path to file
            calculate_checksum: If True, compute MD5 checksum
            stat: Optional pre-fetched stat result

        Returns:
            ScannedFile with metadata
        """
        stat = stat or file_path.stat()
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

    def _iter_scanned_files(
        self,
        directory: Path,
        recursive: bool,
        calculate_checksum: bool,
        follow_symlinks: bool = False,
        on_error: str = "skip",
    ) -> Iterable[Tuple[ScannedFile, Path]]:
        for file_path, relative_path, stat in self._iter_file_entries(
            directory,
            recursive,
            follow_symlinks=follow_symlinks,
            on_error=on_error,
        ):
            try:
                scanned_file = self.scan_file(
                    file_path,
                    calculate_checksum=calculate_checksum,
                    stat=stat,
                )
                yield scanned_file, relative_path
            except Exception as exc:
                _handle_error(on_error, f"Failed to scan file {file_path}", exc)

    def scan_directory(
        self,
        directory: Path,
        recursive: bool = True,
        calculate_checksum: bool = False,
        follow_symlinks: bool = False,
        on_error: str = "skip",
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
            for scanned_file, _ in self._iter_scanned_files(
                directory,
                recursive=recursive,
                calculate_checksum=calculate_checksum,
                follow_symlinks=follow_symlinks,
                on_error=on_error,
            ):
                scanned_files.append(scanned_file)
                logger.debug("Scanned file: %s", scanned_file.path)

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
    follow_symlinks: bool = False,
    on_error: str = "skip",
) -> List[dict]:
    """
    Scan a directory and return PowerShell-parity JSON records.
    """
    root_dir = root_dir.resolve()
    scanner = Scanner(exclude_patterns=exclude_patterns)

    records: List[dict] = []
    for scanned, relative_path in scanner._iter_scanned_files(
        root_dir,
        recursive=recursive,
        calculate_checksum=calculate_checksum,
        follow_symlinks=follow_symlinks,
        on_error=on_error,
    ):
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


def make_record(relative_path: Path, stat: os.stat_result, checksum: str) -> Dict[str, Any]:
    """
    Build a PowerShell-parity record from a relative path and stat data.
    """
    relative_parent = relative_path.parent
    relative_dir = "" if relative_parent == Path(".") else str(relative_parent)

    return {
        "path": relative_dir,
        "filename": relative_path.name,
        "complete_path": str(relative_path),
        "checksum": checksum,
        "size": stat.st_size,
        "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
    }


def write_json_array_stream(
    output_file: Path,
    entries: Iterable[Tuple[Path, Path, os.stat_result]],
    checksum_enabled: bool,
    checksum_workers: int,
    on_error: str,
) -> Tuple[int, int]:
    """
    Stream JSON array to disk while scanning.

    Returns:
        Tuple of (written_count, skipped_count)
    """
    written = 0
    skipped = 0

    buffer: List[Tuple[Path, Path, os.stat_result, Future[str]]] = []
    pipeline_depth = max(4, checksum_workers * 4) if checksum_workers > 1 else 0

    with output_file.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("[\n")

        first = True

        def emit(record: Dict[str, Any]) -> None:
            nonlocal first, written
            if not first:
                handle.write(",\n")
            else:
                first = False

            handle.write(json_pretty_item(record, base_indent=2))
            written += 1

        if checksum_enabled and checksum_workers > 1:
            with ThreadPoolExecutor(max_workers=checksum_workers) as executor:
                for file_path, relative_path, stat in entries:
                    try:
                        future = executor.submit(compute_md5, file_path)
                        buffer.append((file_path, relative_path, stat, future))

                        while len(buffer) >= pipeline_depth:
                            old_path, old_rel, old_stat, old_future = buffer.pop(0)
                            try:
                                checksum = old_future.result()
                                emit(make_record(old_rel, old_stat, checksum))
                            except Exception as exc:
                                skipped += 1
                                _handle_error(
                                    on_error,
                                    f"Failed hashing or writing: {old_path}",
                                    exc,
                                )
                    except Exception as exc:
                        skipped += 1
                        _handle_error(on_error, f"Failed scheduling hashing for: {file_path}", exc)

                while buffer:
                    old_path, old_rel, old_stat, old_future = buffer.pop(0)
                    try:
                        checksum = old_future.result()
                        emit(make_record(old_rel, old_stat, checksum))
                    except Exception as exc:
                        skipped += 1
                        _handle_error(on_error, f"Failed hashing or writing: {old_path}", exc)
        else:
            for file_path, relative_path, stat in entries:
                try:
                    checksum = compute_md5(file_path) if checksum_enabled else ""
                    emit(make_record(relative_path, stat, checksum))
                except Exception as exc:
                    skipped += 1
                    _handle_error(on_error, f"Failed processing: {file_path}", exc)

        handle.write("\n]\n")

    return written, skipped


def files2json(
    input_dir: Path,
    output_dir: Path,
    recursive: bool = True,
    calculate_checksum: bool = False,
    exclude_patterns: Optional[List[str]] = None,
    checksum_workers: int = 1,
    on_error: str = "skip",
    follow_symlinks: bool = False,
    filename_prefix: str = "files",
) -> Tuple[Path, int, int]:
    """
    Scan a directory and write PowerShell-parity JSON output.

    Returns:
        Tuple of (output_file_path, written_count, skipped_count)
    """
    if on_error not in {"fail", "skip"}:
        raise ValueError("on_error must be 'fail' or 'skip'")

    if checksum_workers < 1:
        raise ValueError("checksum_workers must be >= 1")

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / build_output_filename(prefix=filename_prefix)

    scanner = Scanner(exclude_patterns=exclude_patterns)
    entries = scanner._iter_file_entries(
        input_dir,
        recursive=recursive,
        follow_symlinks=follow_symlinks,
        on_error=on_error,
    )

    written, skipped = write_json_array_stream(
        output_file=output_file,
        entries=entries,
        checksum_enabled=calculate_checksum,
        checksum_workers=checksum_workers if calculate_checksum else 1,
        on_error=on_error,
    )

    return output_file, written, skipped


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
        "--checksum-workers",
        type=int,
        default=1,
        help=(
            "Number of worker threads for checksum calculation (only used with --checksum). "
            "Use 1 for sequential; >1 enables parallel hashing. Default: 1"
        ),
    )

    parser.add_argument(
        "--on-error",
        choices=["fail", "skip"],
        default="skip",
        help="Error handling: 'fail' aborts on first error, 'skip' continues. Default: skip",
    )

    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow directory symlinks during scan (default: disabled)",
    )

    parser.add_argument(
        "--output-prefix",
        default="files",
        help="Prefix for the output filename (default: files)",
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

    output_file, record_count, skipped_count = files2json(
        input_dir=root_dir,
        output_dir=output_dir,
        recursive=recursive,
        calculate_checksum=args.checksum,
        exclude_patterns=args.exclude,
        checksum_workers=args.checksum_workers,
        on_error=args.on_error,
        follow_symlinks=args.follow_symlinks,
        filename_prefix=args.output_prefix,
    )

    print(f"Scanned files (written): {record_count}")
    if skipped_count:
        print(f"Skipped files          : {skipped_count}")
    print(f"Output written: {output_file}")


if __name__ == "__main__":
    main()
