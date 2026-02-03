"""
Full pipeline demonstration with mock LLM (no API key required).

This demonstrates the complete pipeline flow:
1. Scanner -> 2. Annotation -> 3. Storage -> 4. Decision -> 5. Planner -> 6. Executor
"""
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from semantic_organizer.models import (
    FileAnnotation,
    FileCategory,
    OrganizationRule,
    PipelineConfig,
)
from semantic_organizer.scanner import Scanner
from semantic_organizer.storage import DatasetStorage
from semantic_organizer.decision import DecisionEngine
from semantic_organizer.planner import Planner
from semantic_organizer.executor import Executor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def mock_annotate_file(scanned_file) -> FileAnnotation:
    """
    Mock annotation function that classifies files based on extension.
    This replaces the LLM call for demonstration purposes.
    """
    path = Path(scanned_file.path)
    ext = path.suffix.lower()

    # Simple rule-based classification
    category_map = {
        '.txt': (FileCategory.DOCUMENT, 'text document', 0.90),
        '.pdf': (FileCategory.DOCUMENT, 'PDF document', 0.95),
        '.doc': (FileCategory.DOCUMENT, 'Word document', 0.92),
        '.jpg': (FileCategory.IMAGE, 'JPEG image', 0.95),
        '.png': (FileCategory.IMAGE, 'PNG image', 0.95),
        '.gif': (FileCategory.IMAGE, 'GIF image', 0.93),
        '.mp4': (FileCategory.VIDEO, 'MP4 video', 0.94),
        '.avi': (FileCategory.VIDEO, 'AVI video', 0.91),
        '.mp3': (FileCategory.AUDIO, 'MP3 audio', 0.94),
        '.wav': (FileCategory.AUDIO, 'WAV audio', 0.92),
        '.py': (FileCategory.CODE, 'Python code', 0.98),
        '.js': (FileCategory.CODE, 'JavaScript code', 0.97),
        '.java': (FileCategory.CODE, 'Java code', 0.97),
        '.zip': (FileCategory.ARCHIVE, 'ZIP archive', 0.99),
        '.tar': (FileCategory.ARCHIVE, 'TAR archive', 0.99),
        '.csv': (FileCategory.DATA, 'CSV data file', 0.96),
        '.json': (FileCategory.DATA, 'JSON data file', 0.97),
    }

    category, desc, confidence = category_map.get(
        ext, 
        (FileCategory.UNKNOWN, 'unknown file type', 0.40)
    )

    return FileAnnotation(
        file_path=scanned_file.path,
        category=category,
        subcategory=None,
        description=f"{desc}: {path.name}",
        suggested_name=None,
        confidence=confidence,
        tags=[category.value, ext[1:]] if ext else [category.value],
        metadata={"extension": ext, "size_bytes": str(scanned_file.size_bytes)}
    )


def main():
    """Run full pipeline demonstration."""
    print("=" * 70)
    print("SEMANTIC FILE ORGANIZER - FULL PIPELINE DEMONSTRATION")
    print("=" * 70)
    print("(Using mock LLM for demonstration - no API key required)")
    print()

    with TemporaryDirectory() as tmpdir:
        # Setup directories
        source_dir = Path(tmpdir) / "source"
        output_dir = Path(tmpdir) / "organized"
        source_dir.mkdir()

        # Create test files
        print("SETUP: Creating test files...")
        test_files = {
            "document1.txt": "This is a text document",
            "report.pdf": "PDF content",
            "photo1.jpg": "image data",
            "photo2.png": "image data",
            "video1.mp4": "video data",
            "music.mp3": "audio data",
            "script.py": "print('hello world')",
            "data.csv": "col1,col2\n1,2",
            "archive.zip": "archive",
            "unknown.xyz": "unknown type",
            "lowconf.abc": "very uncertain",
        }

        for filename, content in test_files.items():
            (source_dir / filename).write_text(content)

        print(f"Created {len(test_files)} test files in {source_dir}\n")

        # STAGE 1: Scanner
        print("=" * 70)
        print("STAGE 1: SCANNING FILES (Read-only)")
        print("=" * 70)
        scanner = Scanner(exclude_patterns=[".*", "__pycache__"])
        scanned_files = scanner.scan_directory(source_dir, recursive=True)
        print(f"✓ Scanned {len(scanned_files)} files")
        for sf in scanned_files[:3]:
            print(f"  - {sf.name} ({sf.size_bytes} bytes)")
        if len(scanned_files) > 3:
            print(f"  ... and {len(scanned_files) - 3} more")
        print()

        # STAGE 2: Annotation (Mock LLM)
        print("=" * 70)
        print("STAGE 2: ANNOTATION (Mock LLM Classification)")
        print("=" * 70)
        annotations = []
        for sf in scanned_files:
            annotation = mock_annotate_file(sf)
            annotations.append(annotation)
            print(f"✓ {sf.name:20s} -> {annotation.category.value:10s} (confidence: {annotation.confidence:.2f})")
        print()

        # STAGE 3: Storage
        print("=" * 70)
        print("STAGE 3: DATASET STORAGE")
        print("=" * 70)
        storage_path = Path(tmpdir) / "annotations.json"
        storage = DatasetStorage(str(storage_path))
        storage.save_annotations(annotations)
        print(f"✓ Saved {len(annotations)} annotations to {storage_path.name}")
        print(f"  File size: {storage_path.stat().st_size} bytes")
        print()

        # STAGE 4: Decision Rules
        print("=" * 70)
        print("STAGE 4: DECISION RULES (Confidence-based filtering)")
        print("=" * 70)
        rules = OrganizationRule(
            min_confidence=0.7,
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
            preserve_structure=False,
            allow_rename=False
        )

        decision_engine = DecisionEngine(rules)
        approved, rejected = decision_engine.filter_annotations(annotations)
        
        print(f"✓ Approved: {len(approved)} files (confidence >= 0.7)")
        for ann in approved:
            print(f"  ✓ {Path(ann.file_path).name:20s} - {ann.category.value}")
        
        print(f"\n✗ Rejected: {len(rejected)} files")
        for ann in rejected:
            print(f"  ✗ {Path(ann.file_path).name:20s} - confidence {ann.confidence:.2f} < 0.7")
        print()

        # STAGE 5: Planner
        print("=" * 70)
        print("STAGE 5: PLANNER (Compute target paths)")
        print("=" * 70)
        planner = Planner(str(output_dir), rules)
        operations = planner.plan_operations(approved)
        
        print(f"✓ Planned {len(operations)} operations:")
        for op in operations:
            src_name = Path(op.source_path).name
            target_rel = Path(op.target_path).relative_to(output_dir) if output_dir in Path(op.target_path).parents else Path(op.target_path)
            print(f"  {op.operation.upper():4s}: {src_name:20s} -> {target_rel}")
        print()

        # STAGE 6: Executor (Dry-run)
        print("=" * 70)
        print("STAGE 6: EXECUTOR (DRY-RUN MODE)")
        print("=" * 70)
        executor = Executor(dry_run=True)
        executed = executor.execute_operations(operations)
        print(f"✓ Would execute {executed} operations")
        print(f"  (No files actually moved in dry-run mode)")
        print()

        # Show that files weren't moved
        print("Verification: Files still in original location:")
        remaining_files = list(source_dir.iterdir())
        print(f"  {len(remaining_files)} files remain in source directory")
        print()

        # STAGE 6b: Executor (Actual execution)
        print("=" * 70)
        print("STAGE 6b: EXECUTOR (ACTUAL EXECUTION)")
        print("=" * 70)
        executor = Executor(dry_run=False)
        executed = executor.execute_operations(operations)
        print(f"✓ Executed {executed} operations successfully")
        print()

        # Verify results
        print("=" * 70)
        print("VERIFICATION: Organized file structure")
        print("=" * 70)
        
        if output_dir.exists():
            for category_dir in sorted(output_dir.iterdir()):
                if category_dir.is_dir():
                    files_in_cat = list(category_dir.iterdir())
                    print(f"  {category_dir.name}/")
                    for f in sorted(files_in_cat):
                        print(f"    - {f.name}")
        
        remaining = list(source_dir.iterdir())
        if remaining:
            print(f"\n  source/ (not moved due to low confidence)")
            for f in sorted(remaining):
                print(f"    - {f.name}")
        
        print()
        
        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"✓ Pipeline completed successfully!")
        print(f"  - Files scanned: {len(scanned_files)}")
        print(f"  - Files annotated: {len(annotations)}")
        print(f"  - Files approved: {len(approved)}")
        print(f"  - Files rejected: {len(rejected)}")
        print(f"  - Operations executed: {executed}")
        print()
        print("This demonstrates the full deterministic pipeline:")
        print("  1. Scanner (read-only)")
        print("  2. Annotation (LLM classification -> structured JSON)")
        print("  3. Storage (persist annotations)")
        print("  4. Decision (confidence-based rules)")
        print("  5. Planner (compute target paths)")
        print("  6. Executor (dry-run + idempotent moves)")
        print()
        print("Key features:")
        print("  ✓ LLM only classifies, never performs file operations")
        print("  ✓ All decisions are explicit and reproducible")
        print("  ✓ Dry-run mode by default")
        print("  ✓ Idempotent operations")
        print("  ✓ Complete audit trail via logging")


if __name__ == "__main__":
    main()
