from __future__ import annotations

import argparse
import logging
from pathlib import Path

from semantic_file_organizer.annotation.annotator import annotate
from semantic_file_organizer.executor.executor import execute
from semantic_file_organizer.planner.planner import plan_action
from semantic_file_organizer.scanner.scanner import scan_directory

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def analyze_command(root: Path, dry_run: bool = True) -> None:
    files = scan_directory(root, dry_run=dry_run)
    summary = []
    for file_record in files:
        annotation = annotate(file_record)
        planned = plan_action(file_record, annotation)
        execute(planned, dry_run=dry_run)
        summary.append(
            f"{planned.action_type.value}: {file_record.path} -> {planned.target_path} "
            f"(category={annotation.category}, confidence={annotation.confidence:.2f})"
        )
    logger.info("Summary:")
    for line in summary:
        logger.info("  %s", line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic File Organizer (dry-run only).")
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser("analyze", help="Scan, annotate, decide, and plan.")
    analyze_parser.add_argument("root", type=Path, help="Root directory to analyze.")
    analyze_parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode (default).")

    args = parser.parse_args()

    if args.command == "analyze":
        analyze_command(args.root, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
