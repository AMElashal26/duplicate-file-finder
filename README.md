# Duplicate File Finder

A safe, read-only Python script that finds duplicate files in any directory tree. Built for reliability and transparency.

---

## Safety Guarantees

```
✅ READ-ONLY OPERATION
   - Only reads files to check names, sizes, and content
   - Never modifies, moves, or deletes any files
   - Reports are written to a separate output location

✅ YOUR FILES ARE NEVER TOUCHED
```

---

## How It Works

### Architecture Overview

```
YOUR FILES (NEVER MODIFIED)
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│  PASS 1: FAST SCAN                                      │
│  Group files by: filename + size                        │
│  Example: "photo.jpg_1024" → [path1, path2, path3]      │
│  Speed: Instant (only reads metadata)                   │
└─────────────────────────────────────────────────────────┘
          │
          ▼ (only candidates with 2+ files)
┌─────────────────────────────────────────────────────────┐
│  PASS 2: HASH VERIFICATION                              │
│  Compute content fingerprint (MD5)                      │
│  Files with identical hash = TRUE duplicates            │
│  Speed: Slower (reads file content)                     │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│  OUTPUT: REPORTS ONLY                                   │
│                                                         │
│  📄 duplicates_report.txt   (human-readable)            │
│  📊 duplicates_data.json    (for further processing)    │
│  📈 statistics_summary.txt  (trade data metrics)        │
└─────────────────────────────────────────────────────────┘
```

### Data Structure Pattern

This uses the **Hash Map Grouping** pattern:

```python
# Dictionary: Key → List of paths
candidates = {
    "photo.jpg_1024": ["/path/a/photo.jpg", "/path/b/photo.jpg"],
    "doc.txt_500": ["/path/c/doc.txt"]  # Only 1 = not duplicate
}
```

**Why Dictionary?**
- O(1) lookup time - checking if key exists is instant
- Perfect for grouping items by common attribute
- Much faster than scanning lists repeatedly

---

## Usage

### Basic Scan
```bash
python3 duplicate_finder.py /path/to/scan
```

### With Options
```bash
# Verbose output (see progress)
python3 duplicate_finder.py /path/to/scan --verbose

# Custom output directory
python3 duplicate_finder.py /path/to/scan --output ./reports

# JSON only (skip text reports)
python3 duplicate_finder.py /path/to/scan --json-only
```

### Help
```bash
python3 duplicate_finder.py --help
```

---

## Safe Testing Workflow

**Never test on real files first.** Use the included test environment generator.

### Step 1: Create Test Sandbox
```bash
python3 create_test_environment.py
```

This creates `test_sandbox/` with:
- Unique files (no duplicates)
- Intentional duplicate sets
- Various file types
- Nested folders

### Step 2: Run on Sandbox
```bash
python3 duplicate_finder.py test_sandbox --verbose
```

### Step 3: Verify Results
Expected output:
- 3 duplicate groups found
- 8 total duplicate files
- 5 removable files

### Step 4: Clean Up
```bash
rm -rf test_sandbox
```

### Step 5: Run on Real Directory
Only after testing works correctly:
```bash
python3 duplicate_finder.py ~/Documents --verbose --output ./my-reports
```

---

## Output Files

### duplicates_report.txt
Human-readable report with:
- Summary statistics
- Breakdown by file type
- Pattern analysis (copy indicators, numbered files)
- Detailed list of every duplicate group

### duplicates_data.json
Structured data for programmatic use:
```json
{
  "metadata": { "scan_directory": "...", "generated_at": "..." },
  "statistics": { "total_groups": 3, "recoverable_size_bytes": 1048576 },
  "patterns": { "copy_patterns": [...], "common_directories": {...} },
  "duplicate_groups": [
    {
      "hash": "abc123...",
      "filename": "photo.jpg",
      "size_bytes": 1024,
      "count": 3,
      "paths": ["/path/a", "/path/b", "/path/c"]
    }
  ]
}
```

### statistics_summary.txt
Quick metrics (trade data):
- Duplicate groups count
- Total duplicate files
- Removable files count
- Space recoverable (by file type)

---

## Development Workflow

### Branching Strategy

Following the two-phase Git workflow:

**Pre-Release (Current Phase):**
```bash
# Direct to main for speed
git add .
git commit -m "feat: add feature"
git push origin main
```

**Post-Release (When Live):**
```bash
# Feature branches required
git checkout -b feat/move-duplicates
# ... work ...
git checkout main
git merge feat/move-duplicates
```

### Branch Naming
```
feat/   - New features (feat/move-duplicates)
fix/    - Bug fixes (fix/hash-error)
docs/   - Documentation (docs/add-examples)
test/   - Testing (test/edge-cases)
```

### Commit Messages
```bash
# Good
git commit -m "feat: add progress bar during hash verification"
git commit -m "fix: handle permission denied errors gracefully"
git commit -m "docs: add usage examples"

# Bad
git commit -m "stuff"
git commit -m "fix"
```

---

## Session Handoff Protocol

**For AI assistants continuing work on this project**

See **[HANDOFF.md](./HANDOFF.md)** for complete session handoff documentation including:
- Current state (all completed features)
- Next tasks (prioritized by phase)
- Branch strategy and guidelines
- Implementation notes and code structure
- Context recovery commands
- Quick handoff template

The handoff document is maintained separately for easy reference and updates.

---

## Recovery Patterns

### If Script Breaks Mid-Scan
The script is read-only - nothing to recover. Just re-run.

### If You Want to Undo Git Changes
```bash
# See recent commits
git log --oneline -5

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

### If Testing on Wrong Directory
No damage possible - script only reads files and writes reports to output directory.

---

## Future Extensions

Planned features (not yet implemented):

- **Move Mode:** `--move /path/to/everything` - Move duplicates to folder
- **Pattern Filing:** Auto-organize based on filename patterns
- **Interactive Mode:** Review each duplicate group before action
- **Dry Run:** Preview what would be moved without doing it

---

## Philosophy

This tool follows these principles:

1. **Safety First** - Read-only by default, explicit action required for changes
2. **Transparency** - Clear reports showing exactly what was found
3. **Reliability** - Two-pass verification ensures no false positives
4. **Simplicity** - One script, no complex dependencies

---

## Requirements

- Python 3.8+
- No external dependencies (uses standard library only)

---

## File Structure

```
duplicate-file-finder/
├── duplicate_finder.py        # Main script
├── create_test_environment.py # Test sandbox generator
├── README.md                  # This file
└── (generated reports)
    ├── duplicates_report.txt
    ├── duplicates_data.json
    └── statistics_summary.txt
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `python3 duplicate_finder.py /path` | Scan directory |
| `python3 duplicate_finder.py /path -v` | Verbose mode |
| `python3 duplicate_finder.py /path -o ./reports` | Custom output |
| `python3 create_test_environment.py` | Create test sandbox |
| `rm -rf test_sandbox` | Clean up test sandbox |

---

**Remember:** This script only reports duplicates. It never modifies your files. You decide what to do with the information.

