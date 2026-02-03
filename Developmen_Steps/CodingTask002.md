# Programming Task: Python File Scanner (PowerShell Parity)

## Task Title

Rebuild an existing PowerShell file-scanning script from scratch in Python

---

## Objective

Implement a **Python-based file scanning script** that reproduces the full functional behavior of an existing PowerShell script (`Files2JSON.ps1`).

The Python implementation must be **read-only**, deterministic, and produce a JSON output that is **structurally equivalent** to the PowerShell output, while being suitable for later integration into a larger semantic file organization pipeline.

---

## Functional Requirements

### 1. Input

The script must accept:

* a root directory to scan (required)
* an output directory for the JSON file (required)
* a flag to enable or disable checksum calculation (optional, default: disabled)

All inputs must be configurable via command-line arguments.

---

### 2. File Scanning Behavior

The script must:

* recursively scan all files under the given root directory
* ignore directories and scan files only
* collect metadata for each file without modifying the file system

The scan must be deterministic and reproducible.

---

### 3. Collected Metadata (per file)

For each file, collect and emit the following fields:

* `path`
  Relative directory path (relative to the root directory)

* `filename`
  Name of the file only (no path)

* `complete_path`
  Full relative path including directories and filename

* `checksum`
  MD5 checksum as a lowercase hexadecimal string, or an empty string if checksum calculation is disabled

* `size`
  File size in bytes (integer)

* `date`
  File modification date in ISO format (`YYYY-MM-DD`)

---

### 4. Checksum Handling

* If checksum calculation is enabled, compute an MD5 hash of the file contents
* If disabled, the checksum field must be an empty string
* The implementation must be efficient and avoid loading entire files into memory at once

---

### 5. Output JSON

The script must:

* output a single JSON file containing a list of file metadata objects
* format the JSON in a stable, readable way (pretty-printed)
* generate the output filename using the current timestamp
* ensure the filename is safe for file systems (no invalid characters)

---

## Non-Functional Requirements

* Python 3.10+
* Use standard library only (no third-party dependencies)
* Use `pathlib` for path handling
* Use `argparse` for CLI arguments
* Use `hashlib` for checksum calculation
* Use `json` for output serialization
* Code must be readable, modular, and testable

---

## Constraints (MUST)

* No file system modifications (read-only)
* No semantic interpretation of filenames or paths
* No machine learning or AI logic
* No background services or watchers
* No parallel execution (single-threaded is sufficient)

---

## Deliverables

* A single runnable Python script
* Clear CLI help output (`--help`)
* Example usage documented in comments

---

## Definition of Done

* Script scans a directory tree successfully
* JSON output matches the PowerShell script output structure
* Optional checksum behavior works as specified
* No files are modified during execution
* Script can be used as a drop-in replacement for the PowerShell scanner
