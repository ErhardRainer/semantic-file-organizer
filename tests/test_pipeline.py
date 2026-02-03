"""
Basic tests for the semantic file organizer pipeline.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from semantic_organizer.models import (
    FileAnnotation,
    FileCategory,
    OrganizationRule,
    ScannedFile,
)
from semantic_organizer.scanner import Scanner
from semantic_organizer.storage import DatasetStorage
from semantic_organizer.decision import DecisionEngine
from semantic_organizer.planner import Planner
from semantic_organizer.executor import Executor


def test_scanner():
    """Test file scanner."""
    with TemporaryDirectory() as tmpdir:
        # Create test files
        test_dir = Path(tmpdir)
        (test_dir / "test1.txt").write_text("test")
        (test_dir / "test2.py").write_text("code")
        (test_dir / ".hidden").write_text("hidden")

        # Scan directory
        scanner = Scanner(exclude_patterns=[".*"])
        files = scanner.scan_directory(test_dir)

        assert len(files) == 2
        assert all(isinstance(f, ScannedFile) for f in files)


def test_storage():
    """Test annotation storage."""
    with TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "annotations.json"
        storage = DatasetStorage(str(storage_path))

        # Create and save annotations
        annotations = [
            FileAnnotation(
                file_path="/test/file.jpg",
                category=FileCategory.IMAGE,
                description="Test image",
                confidence=0.95,
            )
        ]

        storage.save_annotations(annotations)
        assert storage_path.exists()

        # Load annotations
        loaded = storage.load_annotations()
        assert len(loaded) == 1
        assert loaded[0].file_path == "/test/file.jpg"
        assert loaded[0].category == FileCategory.IMAGE


def test_decision_engine():
    """Test decision engine."""
    rules = OrganizationRule(
        min_confidence=0.7,
        category_paths={
            FileCategory.IMAGE: "images",
        },
    )

    engine = DecisionEngine(rules)

    # High confidence annotation
    high_conf = FileAnnotation(
        file_path="/test/high.jpg",
        category=FileCategory.IMAGE,
        description="High confidence",
        confidence=0.95,
    )

    # Low confidence annotation
    low_conf = FileAnnotation(
        file_path="/test/low.jpg",
        category=FileCategory.IMAGE,
        description="Low confidence",
        confidence=0.5,
    )

    approved, rejected = engine.filter_annotations([high_conf, low_conf])
    assert len(approved) == 1
    assert len(rejected) == 1
    assert approved[0].file_path == "/test/high.jpg"


def test_planner():
    """Test operation planner."""
    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        rules = OrganizationRule(
            min_confidence=0.7,
            category_paths={FileCategory.IMAGE: "images"},
        )

        planner = Planner(str(output_dir), rules)

        annotation = FileAnnotation(
            file_path="/source/test.jpg",
            category=FileCategory.IMAGE,
            description="Test",
            confidence=0.95,
        )

        operation = planner.plan_operation(annotation)
        assert operation.source_path == "/source/test.jpg"
        assert "images" in operation.target_path
        assert operation.operation == "move"


def test_executor_dry_run():
    """Test executor in dry-run mode."""
    with TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.txt"
        source.write_text("test")

        annotation = FileAnnotation(
            file_path=str(source),
            category=FileCategory.DOCUMENT,
            description="Test",
            confidence=0.9,
        )

        from semantic_organizer.models import FileOperation

        operation = FileOperation(
            source_path=str(source),
            target_path=str(Path(tmpdir) / "target.txt"),
            operation="move",
            reason="Test",
            annotation=annotation,
        )

        # Dry-run should not move file
        executor = Executor(dry_run=True)
        result = executor.execute_operation(operation)
        assert result is True
        assert source.exists()


def test_executor_actual_move():
    """Test executor with actual file move."""
    with TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source.txt"
        target = Path(tmpdir) / "subdir" / "target.txt"
        source.write_text("test")

        annotation = FileAnnotation(
            file_path=str(source),
            category=FileCategory.DOCUMENT,
            description="Test",
            confidence=0.9,
        )

        from semantic_organizer.models import FileOperation

        operation = FileOperation(
            source_path=str(source),
            target_path=str(target),
            operation="move",
            reason="Test",
            annotation=annotation,
        )

        # Actual move
        executor = Executor(dry_run=False)
        result = executor.execute_operation(operation)
        assert result is True
        assert not source.exists()
        assert target.exists()
        assert target.read_text() == "test"


def test_file_annotation_validation():
    """Test file annotation model validation."""
    # Valid annotation
    annotation = FileAnnotation(
        file_path="/test/file.jpg",
        category=FileCategory.IMAGE,
        description="Test",
        confidence=0.95,
    )
    assert annotation.confidence == 0.95

    # Invalid confidence
    with pytest.raises(ValueError):
        FileAnnotation(
            file_path="/test/file.jpg",
            category=FileCategory.IMAGE,
            description="Test",
            confidence=1.5,  # Invalid: > 1.0
        )

    # Invalid category
    with pytest.raises(ValueError):
        FileAnnotation(
            file_path="/test/file.jpg",
            category="invalid",
            description="Test",
            confidence=0.95,
        )


def test_scanned_file_validation():
    """Test scanned file model validation."""
    from datetime import datetime

    # Valid scanned file
    scanned = ScannedFile(
        path="/absolute/path/file.txt",
        name="file.txt",
        extension=".txt",
        size_bytes=100,
        modified_time=datetime.now(),
    )
    assert scanned.name == "file.txt"

    # Invalid: relative path
    with pytest.raises(ValueError):
        ScannedFile(
            path="relative/path/file.txt",
            name="file.txt",
            extension=".txt",
            size_bytes=100,
            modified_time=datetime.now(),
        )
