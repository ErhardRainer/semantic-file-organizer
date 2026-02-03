"""
CLI interface for semantic file organizer.

Provides command-line interface for running the pipeline.
"""
import argparse
import json
import sys
from pathlib import Path

from semantic_organizer.models import OrganizationRule, PipelineConfig, default_category_paths
from semantic_organizer.pipeline import Pipeline, configure_logging


def create_default_config(source_dir: str, output_dir: str) -> PipelineConfig:
    """
    Create a default pipeline configuration.

    Args:
        source_dir: Source directory to scan
        output_dir: Output directory for organized files

    Returns:
        PipelineConfig with default settings
    """
    # Default category paths
    category_paths = default_category_paths()

    rules = OrganizationRule(
        min_confidence=0.7,
        category_paths=category_paths,
        preserve_structure=False,
        allow_rename=False
    )

    return PipelineConfig(
        source_directory=source_dir,
        output_directory=output_dir,
        annotation_storage=str(Path(output_dir) / "annotations.json"),
        rules=rules,
        llm_model="gpt-3.5-turbo",
        dry_run=True,
        recursive=True
    )


def load_config_file(config_path: str) -> PipelineConfig:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file

    Returns:
        PipelineConfig from file
    """
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    return PipelineConfig(**config_data)


def save_config_file(config: PipelineConfig, config_path: str) -> None:
    """
    Save configuration to JSON file.

    Args:
        config: Configuration to save
        config_path: Path to save config
    """
    with open(config_path, 'w') as f:
        json.dump(config.model_dump(mode='json'), f, indent=2, default=str)
    print(f"Configuration saved to {config_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic File Organizer - Organize files using LLM-based classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run organization (default)
  semantic-organizer --source /path/to/messy/files --output /path/to/organized

  # Actually move files (disable dry-run)
  semantic-organizer --source /path/to/files --output /path/to/organized --no-dry-run

  # Use custom configuration
  semantic-organizer --config config.json

  # Generate example configuration
  semantic-organizer --generate-config example-config.json --source ./input --output ./output
        """
    )

    parser.add_argument(
        "--source",
        type=str,
        help="Source directory to scan for files"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory for organized files"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--generate-config",
        type=str,
        metavar="PATH",
        help="Generate example configuration file and exit"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually move files (default is dry-run)"
    )
    parser.add_argument(
        "--skip-annotation",
        action="store_true",
        help="Skip LLM annotation if annotations already exist"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        help="LLM model to use (default: gpt-3.5-turbo)"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        help="Minimum confidence threshold (0.0-1.0)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Configure logging
    configure_logging(args.log_level)

    # Handle config generation
    if args.generate_config:
        if not args.source or not args.output:
            print("Error: --source and --output required for config generation")
            sys.exit(1)

        source = str(Path(args.source).absolute())
        output = str(Path(args.output).absolute())
        config = create_default_config(source, output)
        save_config_file(config, args.generate_config)
        sys.exit(0)

    # Load or create configuration
    if args.config:
        config = load_config_file(args.config)
    elif args.source and args.output:
        source = str(Path(args.source).absolute())
        output = str(Path(args.output).absolute())
        config = create_default_config(source, output)
    else:
        parser.print_help()
        print("\nError: Either --config or both --source and --output are required")
        sys.exit(1)

    # Override config with CLI arguments
    if args.no_dry_run:
        config.dry_run = False
    if args.model:
        config.llm_model = args.model
    if args.min_confidence is not None:
        config.rules.min_confidence = args.min_confidence

    # Validate directories
    source_path = Path(config.source_directory)
    if not source_path.exists():
        print(f"Error: Source directory does not exist: {source_path}")
        sys.exit(1)

    # Run pipeline
    print(f"Starting semantic file organizer...")
    print(f"Source: {config.source_directory}")
    print(f"Output: {config.output_directory}")
    print(f"Dry-run: {config.dry_run}")
    print(f"Model: {config.llm_model}")
    print()

    try:
        pipeline = Pipeline(config)
        result = pipeline.run(skip_annotation=args.skip_annotation)

        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Files scanned: {result.total_files_scanned}")
        print(f"Files annotated: {result.total_files_annotated}")
        print(f"Files skipped: {result.skipped_files}")
        print(f"Operations planned: {result.total_operations_planned}")
        print(f"Operations executed: {result.total_operations_executed}")

        if config.dry_run:
            print("\nDRY-RUN MODE: No files were actually moved")
            print("Run with --no-dry-run to apply changes")

        sys.exit(0)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
