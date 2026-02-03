"""
Pipeline orchestrator - Coordinates all stages of the file organization pipeline.

This is the main entry point that chains together all pipeline stages:
Scanner -> Annotator -> Storage -> Decision -> Planner -> Executor
"""
import logging
from pathlib import Path
from typing import Optional

from semantic_organizer.annotator import Annotator
from semantic_organizer.decision import DecisionEngine
from semantic_organizer.executor import Executor
from semantic_organizer.models import PipelineConfig, PipelineResult
from semantic_organizer.planner import Planner
from semantic_organizer.scanner import Scanner
from semantic_organizer.storage import DatasetStorage

logger = logging.getLogger(__name__)


class Pipeline:
    """Main pipeline orchestrator for semantic file organization."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline with configuration.

        Args:
            config: Pipeline configuration
        """
        self.config = config

        # Initialize all pipeline components
        self.scanner = Scanner(exclude_patterns=config.exclude_patterns)
        self.annotator = Annotator(model=config.llm_model)
        self.storage = DatasetStorage(config.annotation_storage)
        self.decision_engine = DecisionEngine(config.rules)
        self.planner = Planner(config.output_directory, config.rules)
        self.executor = Executor(dry_run=config.dry_run)

    def run(self, skip_annotation: bool = False) -> PipelineResult:
        """
        Run the complete pipeline.

        Args:
            skip_annotation: If True and annotations exist, skip LLM annotation step

        Returns:
            PipelineResult with execution summary
        """
        result = PipelineResult()

        try:
            # Stage 1: Scanner (read-only)
            logger.info("=" * 60)
            logger.info("STAGE 1: SCANNING FILES")
            logger.info("=" * 60)

            source_dir = Path(self.config.source_directory)
            scanned_files = self.scanner.scan_directory(
                source_dir, 
                recursive=self.config.recursive
            )
            result.total_files_scanned = len(scanned_files)
            logger.info(f"Found {len(scanned_files)} files to process")

            if not scanned_files:
                logger.warning("No files found to organize")
                return result

            # Stage 2: Annotation (LLM) or Load from storage
            logger.info("=" * 60)
            logger.info("STAGE 2: ANNOTATION")
            logger.info("=" * 60)

            if skip_annotation and self.storage.exists():
                logger.info("Loading existing annotations from storage")
                annotations = self.storage.load_annotations()
                
                # Filter annotations to only those in scanned files
                scanned_paths = {sf.path for sf in scanned_files}
                annotations = [a for a in annotations if a.file_path in scanned_paths]
                logger.info(f"Loaded {len(annotations)} relevant annotations")
            else:
                logger.info("Annotating files with LLM")
                annotations = self.annotator.annotate_files(scanned_files)

                # Stage 3: Dataset Storage
                logger.info("=" * 60)
                logger.info("STAGE 3: SAVING ANNOTATIONS")
                logger.info("=" * 60)
                self.storage.save_annotations(annotations)

            result.total_files_annotated = len(annotations)

            if not annotations:
                logger.warning("No annotations generated")
                return result

            # Stage 4: Decision Rules
            logger.info("=" * 60)
            logger.info("STAGE 4: DECISION RULES")
            logger.info("=" * 60)

            approved_annotations, rejected_annotations = self.decision_engine.filter_annotations(
                annotations
            )
            result.skipped_files = len(rejected_annotations)

            if not approved_annotations:
                logger.warning("No files approved for organization")
                return result

            # Stage 5: Planner
            logger.info("=" * 60)
            logger.info("STAGE 5: PLANNING OPERATIONS")
            logger.info("=" * 60)

            operations = self.planner.plan_operations(approved_annotations)
            result.total_operations_planned = len(operations)
            result.operations = operations

            # Stage 6: Executor
            logger.info("=" * 60)
            logger.info("STAGE 6: EXECUTING OPERATIONS")
            logger.info("=" * 60)

            executed = self.executor.execute_operations(operations)
            result.total_operations_executed = executed

            # Summary
            logger.info("=" * 60)
            logger.info("PIPELINE COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Files scanned: {result.total_files_scanned}")
            logger.info(f"Files annotated: {result.total_files_annotated}")
            logger.info(f"Files approved: {len(approved_annotations)}")
            logger.info(f"Files skipped: {result.skipped_files}")
            logger.info(f"Operations planned: {result.total_operations_planned}")
            logger.info(f"Operations executed: {result.total_operations_executed}")

            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result.errors.append(str(e))
            raise


def configure_logging(level: str = "INFO") -> None:
    """
    Configure logging for the pipeline.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
