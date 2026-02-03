#!/usr/bin/env python3
"""
files2json.py

Read-only file system scanner.
Recursively scans a directory and exports file metadata to JSON.

Equivalent in behavior to Files2JSON.ps1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, Dict, Any


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def compute_md5(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute MD5 checksum of a file without loading it fully into memory.
    """
    md5 = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            md5.update(chunk)
    return md5.hexdigest()


def iter_files(root: Path) -> Iterator[Path]:
    """
    Yield all files under root directory recursively.
    """
    for path in root.rglob("*"):
        if path.is_file():
            yield path


# ------------------------------------------------------------
# Core Logic
# ------------------------------------------------------------

def scan_directory(
    root_dir: Path,
    calculate_checksum: bool
) -> list[Dict[str, Any]]:
    """
    Scan directory recursively and return file metadata records.
    """
    records: list[Dict[str, Any]] = []

    for file_path in iter_files(root_dir):
        relative_path = file_path.relative_to(root_dir)

        record = {
            "path": str(relative_path.parent) if relative_path.parent != Path(".") else "",
            "filename": file_path.name,
            "complete_path": str(relative_path),
            "checksum": "",
            "size": file_path.stat().st_size,
            "date": datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).strftime("%Y-%m-%d"),
        }

        if calculate_checksum:
            record["checksum"] = compute_md5(file_path)

        records.append(record)

    return records


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def build_output_filename(prefix: str = "files") -> str:
    """
    Build a filesystem-safe timestamped filename.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively scan a directory and export file metadata to JSON."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Root directory to scan"
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where JSON output will be written"
    )

    parser.add_argument(
        "--checksum",
        action="store_true",
        help="Enable MD5 checksum calculation (default: disabled)"
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    root_dir: Path = args.input_dir.resolve()
    output_dir: Path = args.output_dir.resolve()

    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {root_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    records = scan_directory(
        root_dir=root_dir,
        calculate_checksum=args.checksum
    )

    output_file = output_dir / build_output_filename()

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Scanned files : {len(records)}")
    print(f"Output written: {output_file}")


if __name__ == "__main__":
    main()
