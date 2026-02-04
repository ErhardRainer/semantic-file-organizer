#!/usr/bin/env python3
"""
Agent-Driven Change History Update Script

This script manages an agent-driven change history system that tracks
code changes made by agents/automated systems in the repository.

## Components:

1. **Agent Task Metadata JSON** (`.agent_task.json`):
   - Located at repository root
   - Contains task metadata including date, agent name, and description
   - Automatically created with sensible defaults if missing
   - Invalid JSON is backed up and recreated

2. **History.md** (repository root):
   - Append-only Markdown table tracking all changes
   - Columns: Datum | Agent | Short-Description
   - Never duplicates the last row (idempotency guard)

## Usage:

    # Run with defaults (from repository root)
    python tools/update_history.py

    # Override metadata file location
    python tools/update_history.py --meta /path/to/metadata.json

    # Override history file location
    python tools/update_history.py --history /path/to/History.md

    # Fill JSON fields if they are placeholders
    python tools/update_history.py --agent "my-agent" --short "Added feature X"

    # Specify custom repo root
    python tools/update_history.py --repo-root /path/to/repo

## Agent Workflow:

1. Agent completes a task/job
2. Agent updates `.agent_task.json` with:
   - `date`: Task completion date (ISO 8601 or YYYY-MM-DD)
   - `agent`: Agent identifier (e.g., "copilot", "codex")
   - `short_description`: One-line description of changes
   - Optional: task_id, title, description, changes[], pr, commit, notes
3. Agent runs this script to append to History.md
4. Script is idempotent - safe to run multiple times

## Exit Codes:

- 0: Success (including when creating scaffolds)
- 1: Error (should rarely happen)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


# Default paths relative to repo root
DEFAULT_META_PATH = ".agent_task.json"
DEFAULT_HISTORY_PATH = "History.md"

# Required JSON fields
REQUIRED_FIELDS = ["date", "agent", "short_description"]

# Default values for scaffold
DEFAULT_SCAFFOLD = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "agent": "unknown",
    "short_description": "TODO: describe the change",
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update agent-driven change history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=".",
        help="Repository root directory (default: current directory)",
    )
    parser.add_argument(
        "--meta",
        type=str,
        help=f"Path to metadata JSON file (default: <repo-root>/{DEFAULT_META_PATH})",
    )
    parser.add_argument(
        "--history",
        type=str,
        help=f"Path to History.md file (default: <repo-root>/{DEFAULT_HISTORY_PATH})",
    )
    parser.add_argument(
        "--agent",
        type=str,
        help="Override/fill agent name in JSON if it's 'unknown'",
    )
    parser.add_argument(
        "--short",
        type=str,
        help="Override/fill short description in JSON if it's a placeholder",
    )
    return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> Tuple[Path, Path]:
    """Resolve metadata and history file paths."""
    repo_root = Path(args.repo_root).resolve()
    
    meta_path = Path(args.meta) if args.meta else repo_root / DEFAULT_META_PATH
    history_path = Path(args.history) if args.history else repo_root / DEFAULT_HISTORY_PATH
    
    return meta_path, history_path


def create_scaffold_json(meta_path: Path) -> Dict[str, Any]:
    """Create a scaffold JSON file with default values."""
    scaffold = DEFAULT_SCAFFOLD.copy()
    
    meta_path.write_text(json.dumps(scaffold, indent=2) + "\n")
    print(f"Created scaffold metadata file: {meta_path}")
    
    return scaffold


def backup_invalid_json(meta_path: Path) -> None:
    """Create a timestamped backup of invalid JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = meta_path.with_suffix(f".invalid.{timestamp}.bak")
    backup_path.write_text(meta_path.read_text())
    print(f"Warning: Invalid JSON backed up to: {backup_path}", file=sys.stderr)


def load_or_create_metadata(meta_path: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """Load metadata JSON or create scaffold if missing/invalid."""
    if not meta_path.exists():
        return create_scaffold_json(meta_path)
    
    # Try to load existing JSON
    try:
        with open(meta_path, "r") as f:
            metadata = json.load(f)
    except json.JSONDecodeError:
        # Invalid JSON - backup and create fresh scaffold
        backup_invalid_json(meta_path)
        return create_scaffold_json(meta_path)
    
    # Validate and fill missing required fields
    modified = False
    for field in REQUIRED_FIELDS:
        if field not in metadata or not str(metadata[field]).strip():
            metadata[field] = DEFAULT_SCAFFOLD[field]
            modified = True
            print(f"Warning: Missing/empty field '{field}' filled with default", file=sys.stderr)
    
    # Apply CLI overrides
    if args.agent and metadata["agent"] == "unknown":
        metadata["agent"] = args.agent
        modified = True
    
    if args.short and metadata["short_description"].startswith("TODO:"):
        metadata["short_description"] = args.short
        modified = True
    
    # Save if modified
    if modified:
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")
        print(f"Updated metadata file with defaults/overrides: {meta_path}")
    
    return metadata


def normalize_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format if possible."""
    date_str = str(date_str).strip()
    
    # Already in YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    
    # Try to parse ISO 8601 or other common formats
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(date_str.split("+")[0].split("Z")[0], fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Return as-is if parsing fails
    return date_str


def escape_markdown_cell(text: str) -> str:
    """Escape special characters for Markdown table cells."""
    text = str(text).strip()
    # Collapse whitespace and remove newlines
    text = " ".join(text.split())
    # Escape pipe characters
    text = text.replace("|", "\\|")
    return text


def create_history_table_row(metadata: Dict[str, Any]) -> str:
    """Create a Markdown table row from metadata."""
    date = normalize_date(metadata["date"])
    agent = escape_markdown_cell(metadata["agent"])
    short_desc = escape_markdown_cell(metadata["short_description"])
    
    # Optionally prepend task_id if present
    if "task_id" in metadata and metadata["task_id"]:
        task_id = str(metadata["task_id"]).strip()
        if task_id:
            short_desc = f"[{task_id}] {short_desc}"
    
    return f"| {date} | {agent} | {short_desc} |"


def ensure_history_file(history_path: Path) -> None:
    """Ensure History.md exists with proper header."""
    if not history_path.exists():
        content = [
            "# Change History",
            "",
            "This file tracks agent-driven changes to the project.",
            "",
            "| Datum | Agent | Short-Description |",
            "|-------|-------|-------------------|",
        ]
        history_path.write_text("\n".join(content) + "\n")
        print(f"Created history file: {history_path}")


def get_last_row(history_path: Path) -> Optional[str]:
    """Get the last non-empty row from history file."""
    if not history_path.exists():
        return None
    
    lines = history_path.read_text().splitlines()
    # Find last line starting with '|' (table row)
    for line in reversed(lines):
        if line.strip().startswith("|"):
            return line.strip()
    
    return None


def append_to_history(history_path: Path, metadata: Dict[str, Any]) -> None:
    """Append new row to history file if not duplicate of last row."""
    ensure_history_file(history_path)
    
    new_row = create_history_table_row(metadata)
    last_row = get_last_row(history_path)
    
    # Idempotency guard - don't append if identical to last row
    if last_row == new_row:
        print(f"No changes: last row in {history_path} is identical to new row")
        return
    
    # Append new row
    with open(history_path, "a") as f:
        f.write(new_row + "\n")
    
    print(f"Appended new row to {history_path}")


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    try:
        meta_path, history_path = resolve_paths(args)
        
        # Load or create metadata
        metadata = load_or_create_metadata(meta_path, args)
        
        # Update history
        append_to_history(history_path, metadata)
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
