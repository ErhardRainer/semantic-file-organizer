"""
Example usage of the semantic file organizer pipeline.

This script demonstrates how to use the pipeline programmatically.
"""
from pathlib import Path

from semantic_organizer.models import FileCategory, OrganizationRule, PipelineConfig
from semantic_organizer.pipeline import Pipeline, configure_logging


def main():
    """Run example pipeline."""
    # Configure logging
    configure_logging("INFO")

    # Define organization rules
    rules = OrganizationRule(
        min_confidence=0.7,  # Only organize files with 70%+ confidence
        category_paths={
            FileCategory.DOCUMENT: "documents",
            FileCategory.IMAGE: "images",
            FileCategory.VIDEO: "videos",
            FileCategory.AUDIO: "audio",
            FileCategory.CODE: "code",
            FileCategory.ARCHIVE: "archives",
            FileCategory.DATA: "data",
            FileCategory.UNKNOWN: "unknown",
        },
        preserve_structure=False,  # Don't preserve original directory structure
        allow_rename=False,  # Don't rename files
    )

    # Create pipeline configuration
    config = PipelineConfig(
        source_directory=str(Path("./test_files").absolute()),
        output_directory=str(Path("./organized_files").absolute()),
        annotation_storage="annotations.json",
        rules=rules,
        llm_model="gpt-3.5-turbo",
        dry_run=True,  # Dry-run mode - won't actually move files
        recursive=True,
        exclude_patterns=[".*", "__pycache__", "node_modules"],
    )

    # Create and run pipeline
    print("Starting semantic file organizer pipeline...")
    print(f"Source: {config.source_directory}")
    print(f"Output: {config.output_directory}")
    print(f"Dry-run: {config.dry_run}")
    print()

    pipeline = Pipeline(config)
    result = pipeline.run()

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Files scanned: {result.total_files_scanned}")
    print(f"Files annotated: {result.total_files_annotated}")
    print(f"Files skipped: {result.skipped_files}")
    print(f"Operations planned: {result.total_operations_planned}")
    print(f"Operations executed: {result.total_operations_executed}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")

    if config.dry_run:
        print("\nDRY-RUN MODE: No files were actually moved")
        print("Set dry_run=False to apply changes")


if __name__ == "__main__":
    main()
