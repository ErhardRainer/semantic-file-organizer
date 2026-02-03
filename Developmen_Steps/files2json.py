#!/usr/bin/env python3
"""
files2json.py

Read-only file system scanner.
Recursively scans a directory and exports file metadata to JSON (array).

Parity target: Files2JSON.ps1 output structure.

Fields per file:
- path          (relative directory path, relative to input root)
- filename      (file name only)
- complete_path (relative path including filename)
- checksum      (md5 hex lowercase, or "" if disabled)
- size          (bytes)
- date          (YYYY-MM-DD from mtime, local time)

Notes:
- Deterministic traversal: sorted os.walk directories and filenames
- Optional parallel MD5 hashing (order-preserving)
- Streaming JSON output (no need to hold entire list in memory)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Tuple, Dict, Any


# ------------------------------------------------------------
# Data model (internal)
# ------------------------------------------------------------

@dataclass(frozen=True)
class FileMeta:
    abs_path: Path
    rel_path: Path          # relative to root
    size: int
    mtime: float            # epoch seconds


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def compute_md5(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute MD5 checksum without loading the entire file into memory."""
    md5 = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            md5.update(chunk)
    return md5.hexdigest()


def safe_timestamp() -> str:
    """Return filesystem-safe timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_output_filename(prefix: str = "files") -> str:
    return f"{prefix}_{safe_timestamp()}.json"


def iter_files_deterministic(root: Path, follow_symlinks: bool = False) -> Iterator[FileMeta]:
    """
    Deterministic recursive file iteration using os.walk.
    Directory order and filename order are sorted to make output reproducible.
    """
    root_str = str(root)

    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True, followlinks=follow_symlinks):
        dirnames.sort()
        filenames.sort()

        for name in filenames:
            abs_path = Path(dirpath) / name

            # We only want real files; os.walk gives filenames, but could still be broken links etc.
            try:
                st = abs_path.stat()
            except OSError:
                # Let caller decide how to handle; raise here for strictness
                raise

            rel_path = abs_path.relative_to(root)
            yield FileMeta(
                abs_path=abs_path,
                rel_path=rel_path,
                size=st.st_size,
                mtime=st.st_mtime,
            )


def json_pretty_item(obj: Dict[str, Any], base_indent: int = 2) -> str:
    """
    Serialize a dict as pretty JSON and indent it for embedding into a JSON array.
    Uses only stdlib.
    """
    import json
    txt = json.dumps(obj, ensure_ascii=False, indent=2)
    pad = " " * base_indent
    return "\n".join(pad + line for line in txt.splitlines())


def handle_error(policy: str, msg: str, exc: Optional[BaseException] = None) -> None:
    """
    policy: 'fail' or 'skip'
    """
    if policy == "fail":
        if exc is not None:
            raise exc
        raise RuntimeError(msg)

    # skip
    print(f"[WARN] {msg}", file=sys.stderr)
    if exc is not None:
        print(f"       {type(exc).__name__}: {exc}", file=sys.stderr)


# ------------------------------------------------------------
# Core scanning + writing
# ------------------------------------------------------------

def make_record(meta: FileMeta, checksum: str) -> Dict[str, Any]:
    rel = meta.rel_path
    parent = rel.parent
    return {
        "path": "" if parent == Path(".") else str(parent),
        "filename": rel.name,
        "complete_path": str(rel),
        "checksum": checksum,
        "size": meta.size,
        "date": datetime.fromtimestamp(meta.mtime).strftime("%Y-%m-%d"),
    }


def write_json_array_stream(
    output_file: Path,
    metas: Iterator[FileMeta],
    checksum_enabled: bool,
    checksum_workers: int,
    on_error: str,
) -> Tuple[int, int]:
    """
    Stream JSON array to disk while scanning.
    Returns: (written_count, skipped_count)

    If checksum_enabled and checksum_workers > 1:
      - parallelize MD5 using ThreadPoolExecutor
      - preserve output order using a FIFO buffer of futures
    """
    written = 0
    skipped = 0

    # Order-preserving buffer: (meta, future)
    buffer: list[Tuple[FileMeta, Future[str]]] = []

    # choose buffer size: keep a small pipeline depth
    # (workers * 4 gives enough overlap without too much memory)
    pipeline_depth = max(4, checksum_workers * 4) if checksum_workers > 1 else 0

    with output_file.open("w", encoding="utf-8", newline="\n") as f:
        f.write("[\n")

        first = True

        def emit(record: Dict[str, Any]) -> None:
            nonlocal first, written
            if not first:
                f.write(",\n")
            else:
                first = False

            f.write(json_pretty_item(record, base_indent=2))
            written += 1

        if checksum_enabled and checksum_workers > 1:
            with ThreadPoolExecutor(max_workers=checksum_workers) as ex:
                for meta in metas:
                    try:
                        fut = ex.submit(compute_md5, meta.abs_path)
                        buffer.append((meta, fut))

                        # flush oldest items when buffer is “full”
                        while len(buffer) >= pipeline_depth:
                            old_meta, old_fut = buffer.pop(0)
                            try:
                                chksum = old_fut.result()
                                emit(make_record(old_meta, chksum))
                            except Exception as e:
                                skipped += 1
                                handle_error(on_error, f"Failed hashing or writing: {old_meta.abs_path}", e)

                    except Exception as e:
                        skipped += 1
                        handle_error(on_error, f"Failed scheduling hashing for: {meta.abs_path}", e)

                # flush remaining
                while buffer:
                    old_meta, old_fut = buffer.pop(0)
                    try:
                        chksum = old_fut.result()
                        emit(make_record(old_meta, chksum))
                    except Exception as e:
                        skipped += 1
                        handle_error(on_error, f"Failed hashing or writing: {old_meta.abs_path}", e)

        else:
            # sequential mode (no checksum or checksum sequential)
            for meta in metas:
                try:
                    chksum = ""
                    if checksum_enabled:
                        chksum = compute_md5(meta.abs_path)
                    emit(make_record(meta, chksum))
                except Exception as e:
                    skipped += 1
                    handle_error(on_error, f"Failed processing: {meta.abs_path}", e)

        f.write("\n]\n")

    return written, skipped


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Recursively scan a directory and export file metadata to JSON."
    )

    p.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Root directory to scan",
    )
    p.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where JSON output will be written",
    )
    p.add_argument(
        "--checksum",
        action="store_true",
        help="Enable MD5 checksum calculation (default: disabled)",
    )
    p.add_argument(
        "--checksum-workers",
        type=int,
        default=1,
        help="Number of worker threads for checksum calculation (only used with --checksum). "
             "Use 1 for sequential; >1 enables parallel hashing. Default: 1",
    )
    p.add_argument(
        "--on-error",
        choices=["fail", "skip"],
        default="fail",
        help="Error handling: 'fail' aborts on first error, 'skip' continues and logs warnings. Default: fail",
    )
    p.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow directory symlinks during scan (default: disabled).",
    )
    p.add_argument(
        "--output-prefix",
        default="files",
        help="Prefix for the output filename. Default: files",
    )

    return p.parse_args()


def main() -> None:
    args = parse_args()

    input_dir: Path = args.input_dir.resolve()
    output_dir: Path = args.output_dir.resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist or is not a directory: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / build_output_filename(prefix=args.output_prefix)

    checksum_enabled: bool = bool(args.checksum)
    checksum_workers: int = int(args.checksum_workers)

    if checksum_enabled and checksum_workers < 1:
        raise ValueError("--checksum-workers must be >= 1")

    # Iterator creation can raise on stat errors; handle according to policy
    try:
        metas = iter_files_deterministic(input_dir, follow_symlinks=bool(args.follow_symlinks))
        written, skipped = write_json_array_stream(
            output_file=output_file,
            metas=metas,
            checksum_enabled=checksum_enabled,
            checksum_workers=checksum_workers if checksum_enabled else 1,
            on_error=str(args.on_error),
        )
    except Exception as e:
        # strict behavior by default
        raise

    print(f"Scanned files (written): {written}")
    if skipped:
        print(f"Skipped files          : {skipped}")
    print(f"Output written         : {output_file}")


if __name__ == "__main__":
    main()