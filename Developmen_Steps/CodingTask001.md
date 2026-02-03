# Coding Task: Semantic File Organizer – Phase 1 (Foundation)

## Task Title

Implement the core pipeline skeleton for semantic file classification and deterministic planning

---

## Objective

Create the foundational Python project structure for **Semantic File Organizer** and implement the read-only analysis and planning stages, without performing any file system modifications.

This task establishes the architectural backbone of the project and ensures strict separation between semantic interpretation and execution.

---

## Scope (IN)

### 1. Project Structure

Create a Python package with the following top-level modules:

```
semantic_file_organizer/
├─ scanner/
├─ annotation/
├─ decision/
├─ planner/
├─ executor/
├─ models/
├─ reports/
└─ cli/
```

Each module must contain an `__init__.py`.

---

### 2. Data Models (`models/`)

Define typed data models using `dataclasses` or `pydantic`:

* **FileRecord**

  * path
  * filename
  * size (optional)
  * modified_date (optional)

* **SemanticAnnotation**

  * category
  * series (optional)
  * episode (optional)
  * episode_title (optional)
  * track (optional)
  * confidence (float 0–1)

* **PlannedAction**

  * source_path
  * target_path
  * action_type (`MOVE`, `SKIP`, `REVIEW`)
  * reason

---

### 3. Scanner (`scanner/`)

Implement a read-only scanner that:

* accepts a root directory
* recursively collects file paths
* produces a list of `FileRecord`
* does **not** modify the file system
* supports a dry-run flag (default: true)

---

### 4. Annotation Stub (`annotation/`)

Implement a placeholder annotation service that:

* accepts a `FileRecord`
* returns a mocked `SemanticAnnotation`
* does **not** call an LLM yet
* enforces strict schema validation

This stub will later be replaced by an LLM API call.

---

### 5. Decision Layer (`decision/`)

Implement deterministic decision logic:

* if `confidence >= 0.9` → `MOVE`
* if `0.75 <= confidence < 0.9` → `REVIEW`
* else → `SKIP`

No AI logic allowed here.

---

### 6. Planner (`planner/`)

Implement a planner that:

* takes `FileRecord + SemanticAnnotation`
* computes a deterministic target path
* returns a `PlannedAction`
* does **not** touch the file system

Target paths must be computed using explicit string rules.

---

### 7. Executor Stub (`executor/`)

Implement an executor that:

* accepts `PlannedAction`
* supports `dry_run=True`
* logs intended actions
* does **not** move any files yet

---

### 8. CLI (`cli/`)

Implement a minimal CLI with commands:

```
analyze   # scan + annotate + decide + plan
```

The CLI must:

* print a summary report
* never modify files
* default to dry-run

---

## Constraints (MUST)

* Python only
* No autonomous agents
* No loops that change behavior dynamically
* No file system modification
* All steps must be testable in isolation
* Clear logging for each pipeline stage
* Deterministic behavior only

---

## Explicit Non-Goals (OUT)

* No LLM API integration
* No machine learning
* No file moves or renames
* No UI
* No background services

---

## Deliverables

* Clean, runnable Python project
* Minimal example run via CLI
* Console output showing:

  * scanned files
  * annotations
  * decisions
  * planned target paths

---

## Definition of Done

* Project runs end-to-end in dry-run mode
* No file system changes occur
* Pipeline stages are clearly separated
* Code is readable, typed, and maintainable
