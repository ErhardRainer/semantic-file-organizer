"""
Unit tests for tools/update_history.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.update_history import (
    create_scaffold_json,
    load_or_create_metadata,
    normalize_date,
    escape_markdown_cell,
    create_history_table_row,
    ensure_history_file,
    get_last_row,
    append_to_history,
    DEFAULT_SCAFFOLD,
)


class Args:
    """Mock argparse.Namespace for testing."""
    def __init__(self, repo_root=".", meta=None, history=None, agent=None, short=None):
        self.repo_root = repo_root
        self.meta = meta
        self.history = history
        self.agent = agent
        self.short = short


def test_create_scaffold_json():
    """Test scaffold JSON creation."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        
        scaffold = create_scaffold_json(meta_path)
        
        # Check file was created
        assert meta_path.exists()
        
        # Check scaffold has required fields
        assert "date" in scaffold
        assert "agent" in scaffold
        assert "short_description" in scaffold
        assert scaffold["agent"] == "unknown"
        
        # Check it's valid JSON
        with open(meta_path) as f:
            loaded = json.load(f)
        assert loaded == scaffold


def test_load_or_create_metadata_missing_file():
    """Test metadata loading when file is missing."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        args = Args()
        
        metadata = load_or_create_metadata(meta_path, args)
        
        # File should be created
        assert meta_path.exists()
        assert metadata["agent"] == "unknown"
        assert "TODO:" in metadata["short_description"]


def test_load_or_create_metadata_valid_file():
    """Test metadata loading with valid existing file."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        
        # Create valid JSON
        valid_data = {
            "date": "2026-01-15",
            "agent": "copilot",
            "short_description": "Fixed bug in module X"
        }
        meta_path.write_text(json.dumps(valid_data))
        
        args = Args()
        metadata = load_or_create_metadata(meta_path, args)
        
        assert metadata["agent"] == "copilot"
        assert metadata["short_description"] == "Fixed bug in module X"


def test_load_or_create_metadata_invalid_json():
    """Test handling of invalid JSON with backup."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        
        # Create invalid JSON
        meta_path.write_text("{invalid json content")
        
        args = Args()
        metadata = load_or_create_metadata(meta_path, args)
        
        # Should create scaffold
        assert metadata["agent"] == "unknown"
        
        # Should create backup
        backups = list(Path(tmpdir).glob("*.invalid.*.bak"))
        assert len(backups) == 1
        assert backups[0].read_text() == "{invalid json content"


def test_load_or_create_metadata_missing_required_fields():
    """Test handling of JSON with missing required fields."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        
        # Create JSON missing required fields
        incomplete_data = {"date": "2026-01-15"}
        meta_path.write_text(json.dumps(incomplete_data))
        
        args = Args()
        metadata = load_or_create_metadata(meta_path, args)
        
        # Should fill missing fields with defaults
        assert "agent" in metadata
        assert "short_description" in metadata
        assert metadata["agent"] == "unknown"


def test_load_or_create_metadata_cli_overrides():
    """Test CLI argument overrides."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        
        # Create scaffold (agent="unknown", short_description="TODO:...")
        scaffold_data = DEFAULT_SCAFFOLD.copy()
        meta_path.write_text(json.dumps(scaffold_data))
        
        # Apply overrides
        args = Args(agent="my-agent", short="Did something cool")
        metadata = load_or_create_metadata(meta_path, args)
        
        assert metadata["agent"] == "my-agent"
        assert metadata["short_description"] == "Did something cool"


def test_normalize_date_already_normalized():
    """Test date normalization with already-normalized date."""
    assert normalize_date("2026-01-15") == "2026-01-15"


def test_normalize_date_iso8601():
    """Test date normalization with ISO 8601 timestamp."""
    assert normalize_date("2026-01-15T14:30:00") == "2026-01-15"
    assert normalize_date("2026-01-15T14:30:00.123456") == "2026-01-15"
    assert normalize_date("2026-01-15T14:30:00Z") == "2026-01-15"
    assert normalize_date("2026-01-15T14:30:00+00:00") == "2026-01-15"


def test_normalize_date_with_time():
    """Test date normalization with time."""
    assert normalize_date("2026-01-15 14:30:00") == "2026-01-15"


def test_escape_markdown_cell():
    """Test markdown cell escaping."""
    # Pipe character
    assert escape_markdown_cell("test | value") == "test \\| value"
    
    # Newlines and multiple spaces
    assert escape_markdown_cell("test\nvalue  \n  with\nspaces") == "test value with spaces"
    
    # Leading/trailing whitespace
    assert escape_markdown_cell("  test  ") == "test"


def test_create_history_table_row():
    """Test table row creation."""
    metadata = {
        "date": "2026-01-15",
        "agent": "copilot",
        "short_description": "Fixed bug in module X"
    }
    
    row = create_history_table_row(metadata)
    assert row == "| 2026-01-15 | copilot | Fixed bug in module X |"


def test_create_history_table_row_with_task_id():
    """Test table row creation with task_id."""
    metadata = {
        "date": "2026-01-15",
        "agent": "copilot",
        "short_description": "Fixed bug in module X",
        "task_id": "TASK-123"
    }
    
    row = create_history_table_row(metadata)
    assert row == "| 2026-01-15 | copilot | [TASK-123] Fixed bug in module X |"


def test_create_history_table_row_escaping():
    """Test table row creation with special characters."""
    metadata = {
        "date": "2026-01-15",
        "agent": "copilot",
        "short_description": "Fixed | bug\nwith | pipes"
    }
    
    row = create_history_table_row(metadata)
    assert "\\|" in row  # Escaped pipes
    assert "\n" not in row  # No newlines


def test_ensure_history_file():
    """Test history file creation."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        
        ensure_history_file(history_path)
        
        assert history_path.exists()
        content = history_path.read_text()
        assert "# Change History" in content
        assert "| Datum | Agent | Short-Description |" in content
        assert "|-------|-------|-------------------|" in content


def test_ensure_history_file_already_exists():
    """Test that ensure_history_file doesn't overwrite existing file."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        
        # Create file with custom content
        custom_content = "# My Custom History\n\nCustom content"
        history_path.write_text(custom_content)
        
        ensure_history_file(history_path)
        
        # Should not be overwritten
        assert history_path.read_text() == custom_content


def test_get_last_row():
    """Test getting last row from history."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        
        content = [
            "# Change History",
            "",
            "| Datum | Agent | Short-Description |",
            "|-------|-------|-------------------|",
            "| 2026-01-10 | agent1 | First change |",
            "| 2026-01-15 | agent2 | Second change |",
        ]
        history_path.write_text("\n".join(content))
        
        last_row = get_last_row(history_path)
        assert last_row == "| 2026-01-15 | agent2 | Second change |"


def test_get_last_row_empty_file():
    """Test getting last row from empty history."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        history_path.write_text("# Change History\n\n")
        
        last_row = get_last_row(history_path)
        assert last_row is None


def test_append_to_history_new_entry():
    """Test appending a new entry to history."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        
        metadata = {
            "date": "2026-01-15",
            "agent": "copilot",
            "short_description": "Fixed bug"
        }
        
        append_to_history(history_path, metadata)
        
        content = history_path.read_text()
        assert "| 2026-01-15 | copilot | Fixed bug |" in content


def test_append_to_history_idempotent():
    """Test that appending same entry twice doesn't duplicate."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        
        metadata = {
            "date": "2026-01-15",
            "agent": "copilot",
            "short_description": "Fixed bug"
        }
        
        # Append twice
        append_to_history(history_path, metadata)
        append_to_history(history_path, metadata)
        
        content = history_path.read_text()
        # Should appear only once (plus header row)
        assert content.count("| 2026-01-15 | copilot | Fixed bug |") == 1


def test_append_to_history_multiple_different_entries():
    """Test appending multiple different entries."""
    with TemporaryDirectory() as tmpdir:
        history_path = Path(tmpdir) / "History.md"
        
        metadata1 = {
            "date": "2026-01-15",
            "agent": "copilot",
            "short_description": "First change"
        }
        metadata2 = {
            "date": "2026-01-16",
            "agent": "codex",
            "short_description": "Second change"
        }
        
        append_to_history(history_path, metadata1)
        append_to_history(history_path, metadata2)
        
        content = history_path.read_text()
        assert "| 2026-01-15 | copilot | First change |" in content
        assert "| 2026-01-16 | codex | Second change |" in content


def test_full_workflow_from_scratch():
    """Test complete workflow starting from scratch."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        history_path = Path(tmpdir) / "History.md"
        
        # Step 1: Create scaffold
        args = Args()
        metadata = load_or_create_metadata(meta_path, args)
        
        assert meta_path.exists()
        assert metadata["agent"] == "unknown"
        
        # Step 2: Update history
        append_to_history(history_path, metadata)
        
        assert history_path.exists()
        content = history_path.read_text()
        assert "# Change History" in content
        assert "unknown" in content


def test_full_workflow_with_populated_json():
    """Test complete workflow with populated JSON."""
    with TemporaryDirectory() as tmpdir:
        meta_path = Path(tmpdir) / ".agent_task.json"
        history_path = Path(tmpdir) / "History.md"
        
        # Create populated JSON
        task_data = {
            "date": "2026-02-04",
            "agent": "copilot",
            "short_description": "Implemented change history feature",
            "task_id": "ISSUE-42",
            "changes": [
                {"path": "tools/update_history.py", "type": "added"},
                {"path": "tests/test_update_history.py", "type": "added"}
            ]
        }
        meta_path.write_text(json.dumps(task_data, indent=2))
        
        # Load and update
        args = Args()
        metadata = load_or_create_metadata(meta_path, args)
        append_to_history(history_path, metadata)
        
        content = history_path.read_text()
        assert "[ISSUE-42]" in content
        assert "copilot" in content
        assert "2026-02-04" in content
