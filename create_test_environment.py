#!/usr/bin/env python3
"""
TEST ENVIRONMENT GENERATOR
==========================

This script creates a SAFE test folder with dummy files for testing
the duplicate finder. It creates:

  - Some unique files (no duplicates)
  - Some files that appear multiple times (duplicates)
  - Various file types (.txt, .jpg, .pdf, etc.)
  - Nested folder structure

The test folder is completely isolated - you can delete it anytime.

WHAT THIS CREATES:
    test_sandbox/
    ├── documents/
    │   ├── report.txt          (unique)
    │   ├── notes.txt           (has duplicate in backup/)
    │   └── data.csv            (unique)
    ├── images/
    │   ├── photo1.jpg          (has 2 duplicates)
    │   ├── photo2.jpg          (unique)
    │   └── screenshot.png      (has duplicate)
    ├── backup/
    │   ├── notes.txt           (duplicate of documents/notes.txt)
    │   ├── photo1.jpg          (duplicate)
    │   └── old_stuff/
    │       ├── photo1.jpg      (another duplicate)
    │       └── screenshot.png  (duplicate)
    └── downloads/
        └── photo1 (1).jpg      (duplicate with different name - same content)

USAGE:
    python3 create_test_environment.py

After running, you'll have a safe folder to test with!
"""

import os
import shutil

# Where to create the test environment
TEST_DIR = os.path.join(os.path.dirname(__file__), "test_sandbox")


def create_file(filepath: str, content: str) -> None:
    """Create a file with the given content."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  Created: {filepath}")


def main():
    print("=" * 60)
    print("TEST ENVIRONMENT GENERATOR")
    print("=" * 60)
    print()
    
    # Clean up any existing test directory
    if os.path.exists(TEST_DIR):
        print(f"Removing existing test folder: {TEST_DIR}")
        shutil.rmtree(TEST_DIR)
    
    print(f"\nCreating test folder: {TEST_DIR}\n")
    os.makedirs(TEST_DIR)
    
    # ==========================================================================
    # UNIQUE FILES (no duplicates)
    # ==========================================================================
    print("Creating UNIQUE files (no duplicates):")
    
    create_file(
        os.path.join(TEST_DIR, "documents", "report.txt"),
        "This is a unique report file.\nIt has no duplicates anywhere.\n" * 10
    )
    
    create_file(
        os.path.join(TEST_DIR, "documents", "data.csv"),
        "id,name,value\n1,apple,100\n2,banana,200\n3,cherry,300\n"
    )
    
    create_file(
        os.path.join(TEST_DIR, "images", "photo2.jpg"),
        "FAKE_IMAGE_DATA_UNIQUE_PHOTO_2_" + "x" * 500
    )
    
    # ==========================================================================
    # DUPLICATE SET 1: notes.txt (2 copies)
    # ==========================================================================
    print("\nCreating DUPLICATE SET 1 - notes.txt (2 copies):")
    
    notes_content = "Meeting notes from Monday.\n" * 50
    
    create_file(
        os.path.join(TEST_DIR, "documents", "notes.txt"),
        notes_content
    )
    create_file(
        os.path.join(TEST_DIR, "backup", "notes.txt"),
        notes_content  # EXACT same content = duplicate
    )
    
    # ==========================================================================
    # DUPLICATE SET 2: photo1.jpg (4 copies!)
    # ==========================================================================
    print("\nCreating DUPLICATE SET 2 - photo1.jpg (4 copies):")
    
    photo_content = "FAKE_JPG_HEADER_" + "IMAGE_DATA_BLOCKS_" * 200
    
    create_file(
        os.path.join(TEST_DIR, "images", "photo1.jpg"),
        photo_content
    )
    create_file(
        os.path.join(TEST_DIR, "backup", "photo1.jpg"),
        photo_content  # duplicate
    )
    create_file(
        os.path.join(TEST_DIR, "backup", "old_stuff", "photo1.jpg"),
        photo_content  # duplicate
    )
    create_file(
        os.path.join(TEST_DIR, "downloads", "photo1 (1).jpg"),  # Different name!
        photo_content  # Still a duplicate (same content)
    )
    
    # ==========================================================================
    # DUPLICATE SET 3: screenshot.png (2 copies)
    # ==========================================================================
    print("\nCreating DUPLICATE SET 3 - screenshot.png (2 copies):")
    
    screenshot_content = "PNG_FAKE_HEADER_" + "PIXEL_DATA_" * 100
    
    create_file(
        os.path.join(TEST_DIR, "images", "screenshot.png"),
        screenshot_content
    )
    create_file(
        os.path.join(TEST_DIR, "backup", "old_stuff", "screenshot.png"),
        screenshot_content  # duplicate
    )
    
    # ==========================================================================
    # SAME NAME, DIFFERENT CONTENT (NOT duplicates)
    # ==========================================================================
    print("\nCreating SAME NAME but DIFFERENT CONTENT (NOT duplicates):")
    
    create_file(
        os.path.join(TEST_DIR, "documents", "readme.txt"),
        "This is README version 1.\n" * 20
    )
    create_file(
        os.path.join(TEST_DIR, "backup", "readme.txt"),
        "This is README version 2 - DIFFERENT CONTENT!\n" * 25
    )
    
    # ==========================================================================
    # Summary
    # ==========================================================================
    print("\n" + "=" * 60)
    print("TEST ENVIRONMENT CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"""
Location: {TEST_DIR}

EXPECTED RESULTS when you run the duplicate finder:
─────────────────────────────────────────────────────
  • 3 duplicate groups should be found
  • notes.txt: 2 files (1 removable)
  • photo1.jpg: 4 files (3 removable) - note: includes "photo1 (1).jpg"
  • screenshot.png: 2 files (1 removable)
  
  Total: 8 duplicate files, 5 removable
  
  NOT detected as duplicates (correct behavior):
  • readme.txt - same name but different content
  • report.txt, data.csv, photo2.jpg - unique files

TO TEST THE DUPLICATE FINDER:
─────────────────────────────────────────────────────
  python3 duplicate_finder.py {TEST_DIR} --verbose

TO CLEAN UP WHEN DONE:
─────────────────────────────────────────────────────
  rm -rf {TEST_DIR}
""")


if __name__ == "__main__":
    main()

