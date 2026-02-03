# Semantic File Organizer

A deterministic Python pipeline for semantically classifying and organizing files using LLM-based classification. 

**Key Principles:**
- **Deterministic pipeline, not an autonomous agent**: Clear, reproducible stages
- **LLMs only classify**: Return structured JSON, never perform file operations
- **Explicit decisions**: Confidence-based rules, all operations are auditable
- **Safety first**: Dry-run mode by default, idempotent operations

## Pipeline Architecture

The pipeline consists of 6 distinct stages:

1. **Scanner** (read-only): Scans file system and collects file metadata
2. **Annotation** (LLM): Uses LLM to semantically classify files, returns structured JSON
3. **Dataset Storage**: Persists annotations in JSON for reproducibility
4. **Decision Rules**: Applies confidence-based rules to filter files
5. **Planner**: Computes target paths based on classifications
6. **Executor**: Executes file moves with dry-run support and idempotent behavior

## Installation

```bash
# Clone the repository
git clone https://github.com/ErhardRainer/semantic-file-organizer.git
cd semantic-file-organizer

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

### Basic Usage (Dry-Run)

```bash
# Dry-run (default) - shows what would happen without moving files
semantic-organizer --source /path/to/messy/files --output /path/to/organized
```

### Actually Move Files

```bash
# Disable dry-run to actually move files
semantic-organizer --source /path/to/messy/files --output /path/to/organized --no-dry-run
```

### Use Configuration File

```bash
# Generate example configuration
semantic-organizer --generate-config config.json --source ./input --output ./output

# Run with configuration file
semantic-organizer --config config.json
```

### Advanced Options

```bash
# Skip LLM annotation if annotations already exist
semantic-organizer --config config.json --skip-annotation

# Use different LLM model
semantic-organizer --source ./files --output ./organized --model gpt-4

# Adjust confidence threshold
semantic-organizer --source ./files --output ./organized --min-confidence 0.8

# Enable debug logging
semantic-organizer --source ./files --output ./organized --log-level DEBUG
```

### Standalone Scanner (JSON Export)

If you only want a deterministic file scan with JSON output (PowerShell-parity format),
run the scanner module directly:

```bash
python -m semantic_organizer.scanner --input-dir /path/to/scan --output-dir ./scan-output

# Optional: include MD5 checksums
python -m semantic_organizer.scanner --input-dir /path/to/scan --output-dir ./scan-output --checksum
```

## Configuration File Format

The configuration file is a JSON file with the following structure:

```json
{
  "source_directory": "/absolute/path/to/source",
  "output_directory": "/absolute/path/to/output",
  "annotation_storage": "annotations.json",
  "rules": {
    "min_confidence": 0.7,
    "category_paths": {
      "document": "documents",
      "image": "images",
      "video": "videos",
      "audio": "audio",
      "code": "code",
      "archive": "archives",
      "data": "data",
      "unknown": "unknown"
    },
    "preserve_structure": false,
    "allow_rename": false
  },
  "llm_model": "gpt-3.5-turbo",
  "dry_run": true,
  "recursive": true,
  "exclude_patterns": [".*", "__pycache__", "node_modules"]
}
```

## Module Documentation

### Scanner (`scanner.py`)

Read-only file system scanner that collects file metadata without modifying anything.

```python
from semantic_organizer.scanner import Scanner

scanner = Scanner(exclude_patterns=[".*", "__pycache__"])
scanned_files = scanner.scan_directory(Path("/path/to/files"), recursive=True)
```

Optional checksum computation and JSON export are supported via
`python -m semantic_organizer.scanner`.

### Annotator (`annotator.py`)

LLM-based file classifier that returns structured JSON. The LLM never performs file operations.

```python
from semantic_organizer.annotator import Annotator

annotator = Annotator(model="gpt-3.5-turbo")
annotations = annotator.annotate_files(scanned_files)
```

### Storage (`storage.py`)

Persists and loads annotations in JSON format for reproducibility.

```python
from semantic_organizer.storage import DatasetStorage

storage = DatasetStorage("annotations.json")
storage.save_annotations(annotations)
loaded = storage.load_annotations()
```

### Decision Engine (`decision.py`)

Applies confidence-based rules to determine which files should be organized.

```python
from semantic_organizer.decision import DecisionEngine

engine = DecisionEngine(rules)
approved, rejected = engine.filter_annotations(annotations)
```

### Planner (`planner.py`)

Computes target paths for files based on annotations and rules.

```python
from semantic_organizer.planner import Planner

planner = Planner(output_directory, rules)
operations = planner.plan_operations(approved_annotations)
```

### Executor (`executor.py`)

Executes file operations with dry-run support and idempotent behavior.

```python
from semantic_organizer.executor import Executor

executor = Executor(dry_run=True)
executed_count = executor.execute_operations(operations)
```

### Pipeline (`pipeline.py`)

Main orchestrator that chains all stages together.

```python
from semantic_organizer.pipeline import Pipeline
from semantic_organizer.models import PipelineConfig

config = PipelineConfig(
    source_directory="/path/to/source",
    output_directory="/path/to/output",
    dry_run=True
)

pipeline = Pipeline(config)
result = pipeline.run()
```

## Data Models

All models use Pydantic for validation and JSON schema generation:

- `ScannedFile`: File metadata from scanner
- `FileAnnotation`: LLM-generated classification with confidence
- `FileCategory`: Enum of file categories
- `OrganizationRule`: Confidence thresholds and target paths
- `FileOperation`: Planned file operation (move/copy/skip)
- `PipelineConfig`: Complete pipeline configuration
- `PipelineResult`: Pipeline execution results

## Example Workflow

1. **Scan**: Pipeline scans source directory and collects file metadata
2. **Annotate**: LLM analyzes each file and returns JSON classification:
   ```json
   {
     "category": "image",
     "subcategory": "screenshot",
     "description": "Desktop screenshot",
     "confidence": 0.95,
     "tags": ["screenshot", "desktop"]
   }
   ```
3. **Store**: Annotations saved to `annotations.json` for reproducibility
4. **Decide**: Files with confidence < 0.7 are skipped
5. **Plan**: Target paths computed (e.g., `output/images/screenshot/file.png`)
6. **Execute**: Files moved (or simulated in dry-run mode)

## Safety Features

- **Dry-run by default**: Must explicitly disable to move files
- **Idempotent operations**: Safe to run multiple times
- **Collision handling**: Automatic filename suffixes for duplicates
- **Validation**: All paths validated before operations
- **Logging**: Complete audit trail of all decisions and operations

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=semantic_organizer
```

## License

MIT License

## Contributing

Contributions welcome! Please ensure all tests pass and follow the existing code style.
