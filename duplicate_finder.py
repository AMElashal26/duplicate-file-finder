#!/usr/bin/env python3
"""
================================================================================
DUPLICATE FILE FINDER
================================================================================

A safe, read-only script that finds duplicate files in a directory tree.

SAFETY GUARANTEES:
    ✓ This script ONLY READS files - it never modifies, moves, or deletes
    ✓ Output reports are written to a separate location you specify
    ✓ Your original files are NEVER touched

HOW IT WORKS (Two-Pass Approach):
    
    PASS 1 - Fast Filtering (name + size):
    ┌─────────────────────────────────────────────────────────────────────┐
    │ We walk through every file and create a key: "filename_size"       │
    │                                                                     │
    │ Example: photo.jpg that is 1024 bytes → key = "photo.jpg_1024"     │
    │                                                                     │
    │ If multiple files share the same key, they MIGHT be duplicates.    │
    │ These become "candidates" for Pass 2.                              │
    │                                                                     │
    │ WHY? This is very fast - we only read file metadata, not content.  │
    └─────────────────────────────────────────────────────────────────────┘
    
    PASS 2 - Hash Verification (content fingerprint):
    ┌─────────────────────────────────────────────────────────────────────┐
    │ For each candidate group, we read the actual file content and      │
    │ compute a "hash" (digital fingerprint).                            │
    │                                                                     │
    │ Hash = A unique string generated from file content                  │
    │ If two files have the SAME hash, they have IDENTICAL content.      │
    │                                                                     │
    │ WHY two passes? Speed! Hash computation is slow (reads whole file) │
    │ By filtering first, we only hash the likely duplicates.            │
    └─────────────────────────────────────────────────────────────────────┘

DATA STRUCTURE PATTERN:
    
    This uses the "Hash Map Grouping" pattern - a common algorithm approach:
    
    Dictionary (Hash Map):
        Key   → Value
        ───────────────
        "filename_size" → [list of file paths with this key]
    
    Example:
        {
            "photo.jpg_1024": ["/path/a/photo.jpg", "/path/b/photo.jpg"],
            "doc.txt_500":    ["/path/c/doc.txt"]  # Only 1 file = not a duplicate
        }
    
    Why Dictionary/Hash Map?
        - O(1) average lookup time - checking if a key exists is instant
        - Perfect for grouping items by a common attribute
        - Much faster than scanning through a list every time

OUTPUT FILES:
    
    duplicates_report.txt   - Human-readable report with all details
    duplicates_data.json    - Machine-readable data for further processing
    statistics_summary.txt  - Quick stats: types, counts, space savings

USAGE:
    
    python3 duplicate_finder.py /path/to/scan                    # Basic scan
    python3 duplicate_finder.py /path/to/scan --output ./reports # Custom output dir
    python3 duplicate_finder.py /path/to/scan --verbose          # Show progress

Author: Generated with Claude AI
Version: 1.0
License: MIT
================================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================
# 
# os          - For walking directories and getting file info
# hashlib     - For computing content fingerprints (MD5 hash)
# json        - For writing JSON reports
# argparse    - For parsing command-line arguments
# re          - For pattern matching (regex) in filenames
# collections - For defaultdict (dictionary with default values)
# datetime    - For timestamps in reports
# pathlib     - For path manipulation (not heavily used here)
# typing      - For type hints (makes code more readable)
# =============================================================================

import os
import hashlib
import json
import argparse
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set


# =============================================================================
# PASS 1: CORE SCANNER
# =============================================================================
# 
# Purpose: Quickly find files that MIGHT be duplicates based on name + size
# 
# Why name + size? Two files with the same name and same size are likely
# to be duplicates. This is much faster than reading file content.
#
# Data Structure: Dictionary where
#   Key   = "filename_size" (e.g., "photo.jpg_1024")  
#   Value = List of full paths to files with that key
#
# =============================================================================

def scan_directory(root_path: str, verbose: bool = False) -> Dict[str, List[str]]:
    """
    Recursively scan a directory tree and group files by filename + size.
    
    This is PASS 1 of our duplicate detection - the fast filtering step.
    
    HOW IT WORKS:
    ─────────────
    1. os.walk() gives us every folder and file in the tree
    2. For each file, we create a key: "filename_size"
    3. Files with the same key go into the same list
    4. At the end, we keep only groups with 2+ files (potential duplicates)
    
    Args:
        root_path: The folder to scan (and all subfolders)
        verbose: If True, print progress updates
    
    Returns:
        Dictionary mapping "filename_size" → [list of file paths]
        Only includes entries with 2+ files (potential duplicates)
    
    Example:
        scan_directory("/Users/me/Documents")
        # Returns:
        # {
        #     "photo.jpg_1024": ["/Users/me/Documents/photo.jpg", 
        #                        "/Users/me/Documents/backup/photo.jpg"],
        #     "notes.txt_500": ["/Users/me/Documents/notes.txt",
        #                       "/Users/me/Documents/old/notes.txt"]
        # }
    """
    # defaultdict(list) creates an empty list automatically for new keys
    # This saves us from writing: if key not in dict: dict[key] = []
    candidates = defaultdict(list)
    file_count = 0
    
    # os.walk() is a generator that yields (dirpath, dirnames, filenames)
    # for every directory in the tree, including nested ones
    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            # Build the full path to the file
            filepath = os.path.join(dirpath, filename)
            
            try:
                # Get file size in bytes (this is fast - just reads metadata)
                file_size = os.path.getsize(filepath)
                
                # Create our grouping key: "filename_size"
                # Example: "photo.jpg_1024"
                key = f"{filename}_{file_size}"
                
                # Add this file path to the list for this key
                candidates[key].append(filepath)
                file_count += 1
                
                # Progress indicator every 1000 files
                if verbose and file_count % 1000 == 0:
                    print(f"  Scanned {file_count} files...")
                    
            except (OSError, PermissionError) as e:
                # Some files might not be accessible (permission denied, etc.)
                # We skip these gracefully and continue
                if verbose:
                    print(f"Warning: Could not access {filepath}: {e}")
    
    if verbose:
        print(f"  Total files scanned: {file_count}")
    
    # Filter: only keep entries where len(value) > 1
    # A single file can't be a duplicate of itself!
    # 
    # This is a dictionary comprehension - a compact way to filter
    # Equivalent to:
    #   result = {}
    #   for k, v in candidates.items():
    #       if len(v) > 1:
    #           result[k] = v
    return {k: v for k, v in candidates.items() if len(v) > 1}


# =============================================================================
# PASS 2: HASH VERIFICATION
# =============================================================================
#
# Purpose: Confirm that candidate duplicates are TRUE duplicates by comparing
#          their actual content using cryptographic hashes (fingerprints).
#
# What is a Hash?
#   A hash function takes any data and produces a fixed-size "fingerprint"
#   - Same input → always same output
#   - Different input → (almost always) different output
#   - You can't reverse a hash to get the original data
#
# We use MD5 which produces a 32-character hexadecimal string like:
#   "d41d8cd98f00b204e9800998ecf8427e"
#
# If two files produce the same hash, their content is identical.
#
# =============================================================================

def compute_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """
    Compute the MD5 hash (fingerprint) of a file's content.
    
    WHY CHUNKS?
    ───────────
    Large files (gigabytes) can't fit in memory all at once.
    We read in small chunks (8KB default) and update the hash incrementally.
    This is memory-efficient - we only use 8KB regardless of file size.
    
    Args:
        filepath: Path to the file to hash
        chunk_size: How many bytes to read at a time (default 8KB)
    
    Returns:
        32-character hexadecimal hash string, or None if file can't be read
    
    Example:
        compute_file_hash("/path/to/photo.jpg")
        # Returns: "a1b2c3d4e5f6..."
    """
    # Create a new MD5 hash object
    hasher = hashlib.md5()
    
    try:
        # 'rb' = read binary mode (works for any file type)
        with open(filepath, 'rb') as f:
            # The walrus operator := reads a chunk and assigns it to 'chunk'
            # Loop continues while chunk is not empty (not at end of file)
            while chunk := f.read(chunk_size):
                # Update the hash with this chunk of data
                hasher.update(chunk)
        
        # hexdigest() returns the hash as a readable hex string
        return hasher.hexdigest()
        
    except (OSError, PermissionError) as e:
        # File might be locked, deleted, or permission denied
        print(f"Warning: Could not hash {filepath}: {e}")
        return None


def verify_duplicates(candidates: Dict[str, List[str]], verbose: bool = False) -> Dict[str, List[str]]:
    """
    Verify candidate duplicates by computing content hashes.
    
    This is PASS 2 - we only run this on files that passed Pass 1.
    
    HOW IT WORKS:
    ─────────────
    For each group of candidates (files with same name+size):
    1. Compute the hash of each file
    2. Group files by their hash
    3. Files with identical hashes are TRUE duplicates
    
    Args:
        candidates: Dictionary from scan_directory() - potential duplicates
        verbose: If True, print progress updates
    
    Returns:
        Dictionary mapping "content_hash" → [list of duplicate file paths]
        Only includes entries with 2+ files (confirmed duplicates)
    
    WHY NEW DICTIONARY?
    ───────────────────
    We create a new dictionary keyed by hash because:
    - Some "candidates" might have same name+size but different content
    - Some files with DIFFERENT names might have SAME content
    - Hash is the definitive test for "same content"
    """
    duplicates = defaultdict(list)
    total_groups = len(candidates)
    processed = 0
    
    for name_size_key, paths in candidates.items():
        processed += 1
        if verbose and processed % 100 == 0:
            print(f"  Hashing group {processed}/{total_groups}...")
        
        # Group these specific files by their content hash
        hash_groups = defaultdict(list)
        
        for path in paths:
            file_hash = compute_file_hash(path)
            if file_hash:  # None means file couldn't be read
                hash_groups[file_hash].append(path)
        
        # Transfer confirmed duplicates to our result
        for file_hash, hash_paths in hash_groups.items():
            if len(hash_paths) > 1:  # 2+ files with same hash = duplicates
                duplicates[file_hash].extend(hash_paths)
    
    return dict(duplicates)


# =============================================================================
# STATISTICS ENGINE
# =============================================================================
#
# Purpose: Calculate useful statistics about the duplicates found
#
# Key Metrics:
#   - Total duplicate groups (sets of files that are copies of each other)
#   - Total duplicate files (sum of all files across all groups)
#   - Removable files (keeping one from each group, how many can we delete?)
#   - Space that could be recovered (in bytes and human-readable)
#   - Breakdown by file extension (which types waste the most space?)
#
# =============================================================================

def calculate_statistics(duplicates: Dict[str, List[str]]) -> dict:
    """
    Calculate comprehensive statistics about duplicate files.
    
    WHAT WE CALCULATE:
    ──────────────────
    - total_groups: Number of duplicate sets found
    - total_duplicate_files: Total count of all duplicate files
    - total_files_removable: Files that could be deleted (keeping one per group)
    - total_size_bytes: Combined size of all duplicate files
    - recoverable_size_bytes: Space saved if we delete removable files
    - by_extension: All stats broken down by file type (.jpg, .txt, etc.)
    
    Args:
        duplicates: Dictionary from verify_duplicates() - confirmed duplicates
    
    Returns:
        Dictionary containing all statistics
    
    Example Output:
        {
            "total_groups": 3,
            "total_duplicate_files": 8,
            "total_files_removable": 5,
            "recoverable_size_bytes": 1048576,
            "by_extension": {
                ".jpg": {"groups": 2, "removable_files": 4, ...},
                ".txt": {"groups": 1, "removable_files": 1, ...}
            }
        }
    """
    stats = {
        "total_groups": len(duplicates),
        "total_duplicate_files": 0,
        "total_files_removable": 0,
        "total_size_bytes": 0,
        "recoverable_size_bytes": 0,
        # defaultdict with a lambda creates nested default structure
        "by_extension": defaultdict(lambda: {
            "groups": 0,
            "total_files": 0,
            "removable_files": 0,
            "total_size": 0,
            "recoverable_size": 0
        })
    }
    
    for file_hash, paths in duplicates.items():
        num_files = len(paths)
        stats["total_duplicate_files"] += num_files
        stats["total_files_removable"] += num_files - 1  # Keep one from each group
        
        # Get file size (all files in group have same size since same content)
        try:
            file_size = os.path.getsize(paths[0])
        except OSError:
            file_size = 0
        
        # Calculate sizes
        total_size = file_size * num_files           # All copies combined
        recoverable = file_size * (num_files - 1)    # What we'd save keeping one
        
        stats["total_size_bytes"] += total_size
        stats["recoverable_size_bytes"] += recoverable
        
        # Get file extension (e.g., ".jpg", ".txt")
        # os.path.splitext returns (name, extension)
        ext = os.path.splitext(paths[0])[1].lower() or "(no extension)"
        
        # Update per-extension statistics
        stats["by_extension"][ext]["groups"] += 1
        stats["by_extension"][ext]["total_files"] += num_files
        stats["by_extension"][ext]["removable_files"] += num_files - 1
        stats["by_extension"][ext]["total_size"] += total_size
        stats["by_extension"][ext]["recoverable_size"] += recoverable
    
    # Convert defaultdict to regular dict (needed for JSON serialization)
    stats["by_extension"] = dict(stats["by_extension"])
    
    return stats


def format_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format (KB, MB, GB, etc.)
    
    Args:
        size_bytes: Size in bytes (integer)
    
    Returns:
        Human-readable string like "1.50 MB"
    
    Example:
        format_size(1536) → "1.50 KB"
        format_size(1048576) → "1.00 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# =============================================================================
# PATTERN ANALYSIS
# =============================================================================
#
# Purpose: Identify common patterns in duplicate filenames to help understand
#          WHY duplicates exist and HOW to organize them.
#
# Common Patterns:
#   - Copy indicators: "file (1).txt", "file - Copy.txt", "file_copy.txt"
#   - Numbered sequences: "photo_001.jpg", "photo_002.jpg"
#   - Common prefixes: Many files starting with "IMG_" or "Screenshot"
#   - Hot spots: Directories containing many duplicates
#
# This helps you make informed decisions about cleanup strategies.
#
# =============================================================================

def analyze_filename_patterns(duplicates: Dict[str, List[str]]) -> dict:
    """
    Analyze filename patterns to identify duplication causes.
    
    PATTERNS DETECTED:
    ──────────────────
    1. Copy indicators: Files with " (1)", " - Copy", "_copy" in name
    2. Numbered patterns: Files with numbers like "(1)", "_01", "[2]"
    3. Common prefixes: Files sharing the same first 5 characters
    4. Hot directories: Folders containing the most duplicates
    
    Args:
        duplicates: Dictionary of confirmed duplicates
    
    Returns:
        Dictionary with pattern analysis results
    
    WHY THIS MATTERS:
    ─────────────────
    - If many files have "(1)" → You've been copying files a lot
    - If one directory has many duplicates → That's a cleanup hot spot
    - Common prefixes help identify categories (photos, screenshots, etc.)
    """
    patterns = {
        "copy_patterns": [],           # Files with copy indicators
        "numbered_patterns": [],       # Files with numbers
        "common_prefixes": {},         # Shared prefixes
        "common_directories": defaultdict(int)  # Count per directory
    }
    
    # REGEX EXPLANATION:
    # ──────────────────
    # [\s\-_]* matches optional spaces, dashes, underscores
    # (copy|...) matches various copy indicators
    # \(\d+\) matches (1), (2), etc.
    # re.IGNORECASE makes it case-insensitive
    copy_regex = re.compile(r'[\s\-_]*(copy|копия|\(\d+\)|\s\d+)[\s\-_]*', re.IGNORECASE)
    
    # Matches: (1), [2], _3, etc.
    numbered_regex = re.compile(r'[\(\[\s](\d+)[\)\]\s]|_(\d+)(?=\.|$)')
    
    all_filenames = []
    
    for file_hash, paths in duplicates.items():
        for path in paths:
            filename = os.path.basename(path)  # Just the filename, no directory
            dirname = os.path.dirname(path)    # Just the directory path
            
            all_filenames.append(filename)
            patterns["common_directories"][dirname] += 1
            
            # Check for copy-style patterns
            if copy_regex.search(filename):
                patterns["copy_patterns"].append({
                    "file": filename,
                    "path": path
                })
            
            # Check for numbered patterns
            if numbered_regex.search(filename):
                patterns["numbered_patterns"].append({
                    "file": filename,
                    "path": path
                })
    
    # Find common prefixes
    # Group files by their first 5 characters
    prefix_groups = defaultdict(list)
    for filename in all_filenames:
        if len(filename) >= 5:
            prefix = filename[:5].lower()
            prefix_groups[prefix].append(filename)
    
    # Only keep prefixes shared by 3+ files (meaningful groups)
    patterns["common_prefixes"] = {
        k: v for k, v in prefix_groups.items() if len(v) > 2
    }
    
    # Sort directories by duplicate count, keep top 10
    sorted_dirs = sorted(
        patterns["common_directories"].items(),
        key=lambda x: x[1],  # Sort by count
        reverse=True         # Highest first
    )[:10]
    patterns["common_directories"] = dict(sorted_dirs)
    
    # Limit lists to avoid massive reports
    patterns["copy_patterns"] = patterns["copy_patterns"][:50]
    patterns["numbered_patterns"] = patterns["numbered_patterns"][:50]
    
    return patterns


# =============================================================================
# REPORT GENERATORS
# =============================================================================
#
# Purpose: Create output files that present the findings in useful formats
#
# We generate THREE files:
#   1. duplicates_report.txt - Full human-readable report
#   2. duplicates_data.json  - Structured data for programs
#   3. statistics_summary.txt - Quick overview of key stats
#
# Why multiple formats?
#   - TXT is easy to read in any text editor
#   - JSON can be processed by other scripts/programs
#   - Summary gives quick answers without reading full report
#
# =============================================================================

def generate_text_report(
    duplicates: Dict[str, List[str]],
    stats: dict,
    patterns: dict,
    output_path: str,
    root_path: str
) -> None:
    """
    Generate a detailed human-readable text report.
    
    REPORT STRUCTURE:
    ─────────────────
    1. Header with scan info and timestamp
    2. Summary statistics
    3. Breakdown by file type
    4. Pattern analysis findings
    5. Detailed list of every duplicate group
    
    Args:
        duplicates: Confirmed duplicate file groups
        stats: Statistics dictionary
        patterns: Pattern analysis results
        output_path: Where to save the report
        root_path: The directory that was scanned
    
    SAFETY NOTE:
    ────────────
    This creates a NEW file at output_path.
    It does NOT modify any of the scanned files.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("DUPLICATE FILE FINDER REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Scan Directory: {root_path}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary Statistics
        f.write("-" * 40 + "\n")
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Duplicate Groups Found:    {stats['total_groups']}\n")
        f.write(f"Total Duplicate Files:     {stats['total_duplicate_files']}\n")
        f.write(f"Files That Can Be Removed: {stats['total_files_removable']}\n")
        f.write(f"Total Size of Duplicates:  {format_size(stats['total_size_bytes'])}\n")
        f.write(f"Recoverable Space:         {format_size(stats['recoverable_size_bytes'])}\n\n")
        
        # By File Type
        f.write("-" * 40 + "\n")
        f.write("BY FILE TYPE\n")
        f.write("-" * 40 + "\n")
        f.write(f"{'Extension':<15} {'Groups':>8} {'Files':>8} {'Removable':>10} {'Recoverable':>12}\n")
        f.write("-" * 55 + "\n")
        
        # Sort by recoverable space (biggest savings first)
        sorted_ext = sorted(
            stats['by_extension'].items(),
            key=lambda x: x[1]['recoverable_size'],
            reverse=True
        )
        
        for ext, data in sorted_ext:
            f.write(f"{ext:<15} {data['groups']:>8} {data['total_files']:>8} "
                   f"{data['removable_files']:>10} {format_size(data['recoverable_size']):>12}\n")
        
        f.write("\n")
        
        # Pattern Analysis
        f.write("-" * 40 + "\n")
        f.write("PATTERN ANALYSIS\n")
        f.write("-" * 40 + "\n")
        
        if patterns['copy_patterns']:
            f.write(f"\nFiles with copy indicators ({len(patterns['copy_patterns'])} found):\n")
            for item in patterns['copy_patterns'][:10]:
                f.write(f"  - {item['file']}\n")
            if len(patterns['copy_patterns']) > 10:
                f.write(f"  ... and {len(patterns['copy_patterns']) - 10} more\n")
        
        if patterns['numbered_patterns']:
            f.write(f"\nFiles with numbered patterns ({len(patterns['numbered_patterns'])} found):\n")
            for item in patterns['numbered_patterns'][:10]:
                f.write(f"  - {item['file']}\n")
            if len(patterns['numbered_patterns']) > 10:
                f.write(f"  ... and {len(patterns['numbered_patterns']) - 10} more\n")
        
        if patterns['common_directories']:
            f.write(f"\nDirectories with most duplicates:\n")
            for dirname, count in list(patterns['common_directories'].items())[:5]:
                f.write(f"  - {dirname}: {count} duplicates\n")
        
        f.write("\n")
        
        # Detailed Groups
        f.write("=" * 80 + "\n")
        f.write("DUPLICATE GROUPS (Detailed)\n")
        f.write("=" * 80 + "\n\n")
        
        for i, (file_hash, paths) in enumerate(duplicates.items(), 1):
            try:
                file_size = os.path.getsize(paths[0])
            except OSError:
                file_size = 0
            
            filename = os.path.basename(paths[0])
            f.write(f"Group {i}: {filename}\n")
            f.write(f"  Hash: {file_hash}\n")
            f.write(f"  Size: {format_size(file_size)}\n")
            f.write(f"  Copies: {len(paths)}\n")
            f.write(f"  Locations:\n")
            for path in paths:
                f.write(f"    - {path}\n")
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


def generate_json_report(
    duplicates: Dict[str, List[str]],
    stats: dict,
    patterns: dict,
    output_path: str,
    root_path: str
) -> None:
    """
    Generate a JSON report for programmatic processing.
    
    WHY JSON?
    ─────────
    JSON (JavaScript Object Notation) is a standard data format that:
    - Can be read by any programming language
    - Is structured and easy to parse
    - Can be used to build additional tools (like a file mover)
    
    Args:
        duplicates: Confirmed duplicate file groups
        stats: Statistics dictionary  
        patterns: Pattern analysis results
        output_path: Where to save the JSON file
        root_path: The directory that was scanned
    """
    # Build detailed list of duplicate groups
    duplicate_groups = []
    for file_hash, paths in duplicates.items():
        try:
            file_size = os.path.getsize(paths[0])
        except OSError:
            file_size = 0
        
        duplicate_groups.append({
            "hash": file_hash,
            "filename": os.path.basename(paths[0]),
            "size_bytes": file_size,
            "size_human": format_size(file_size),
            "count": len(paths),
            "paths": paths
        })
    
    # Assemble full report
    report = {
        "metadata": {
            "scan_directory": root_path,
            "generated_at": datetime.now().isoformat(),
            "version": "1.0"
        },
        "statistics": stats,
        "patterns": patterns,
        "duplicate_groups": duplicate_groups
    }
    
    # Write with pretty formatting (indent=2 makes it readable)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_statistics_summary(stats: dict, output_path: str) -> None:
    """
    Generate a concise statistics-only summary file.
    
    This is the "trade data" you mentioned - quick metrics for analysis.
    
    Args:
        stats: Statistics dictionary
        output_path: Where to save the summary
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("DUPLICATE FILES - STATISTICS SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("TRADE DATA\n")
        f.write("-" * 30 + "\n")
        f.write(f"{'Metric':<30} {'Value':>15}\n")
        f.write("-" * 45 + "\n")
        f.write(f"{'Duplicate Groups':<30} {stats['total_groups']:>15}\n")
        f.write(f"{'Total Duplicate Files':<30} {stats['total_duplicate_files']:>15}\n")
        f.write(f"{'Removable Files':<30} {stats['total_files_removable']:>15}\n")
        f.write(f"{'Space Recoverable':<30} {format_size(stats['recoverable_size_bytes']):>15}\n\n")
        
        f.write("BY FILE TYPE (sorted by recoverable space)\n")
        f.write("-" * 50 + "\n")
        
        sorted_ext = sorted(
            stats['by_extension'].items(),
            key=lambda x: x[1]['recoverable_size'],
            reverse=True
        )
        
        for ext, data in sorted_ext:
            f.write(f"\n{ext}:\n")
            f.write(f"  Files Moved (potential):  {data['removable_files']}\n")
            f.write(f"  Space Saved (potential):  {format_size(data['recoverable_size'])}\n")


# =============================================================================
# COMMAND LINE INTERFACE (CLI)
# =============================================================================
#
# Purpose: Allow the script to be run from the terminal with arguments
#
# Usage Examples:
#   python3 duplicate_finder.py /path/to/scan
#   python3 duplicate_finder.py /path/to/scan --output ./reports
#   python3 duplicate_finder.py /path/to/scan --verbose
#   python3 duplicate_finder.py --help
#
# The argparse library handles:
#   - Parsing command-line arguments
#   - Validating required arguments
#   - Generating help text automatically
#
# =============================================================================

def main():
    """
    Main entry point - orchestrates the entire duplicate finding process.
    
    EXECUTION FLOW:
    ───────────────
    1. Parse command-line arguments
    2. Validate input directory exists
    3. Run Pass 1: Scan and group by name+size
    4. Run Pass 2: Verify with content hash
    5. Calculate statistics
    6. Analyze patterns
    7. Generate all reports
    8. Print summary to console
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Find duplicate files in a directory tree. SAFE: Only reads files, never modifies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SAFETY NOTE:
  This script ONLY READS files. It never modifies, moves, or deletes anything.
  Reports are written to new files in the output directory.

Examples:
  %(prog)s /path/to/scan
  %(prog)s /path/to/scan --output ./reports
  %(prog)s . --verbose
  %(prog)s ~/Downloads --verbose --output ~/Desktop/reports
        """
    )
    
    # Required argument: directory to scan
    parser.add_argument(
        'directory',
        help='Directory to scan for duplicates (will include all subfolders)'
    )
    
    # Optional: where to save reports
    parser.add_argument(
        '-o', '--output',
        default='.',
        help='Output directory for reports (default: current directory)'
    )
    
    # Optional: show progress
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print progress information during scan'
    )
    
    # Optional: only JSON output
    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Only generate JSON report (skip text reports)'
    )
    
    args = parser.parse_args()
    
    # Validate the input directory
    root_path = os.path.abspath(args.directory)
    if not os.path.isdir(root_path):
        print(f"Error: '{args.directory}' is not a valid directory")
        return 1
    
    # Create output directory if it doesn't exist
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    # =========================================================================
    # PASS 1: Fast scan by filename + size
    # =========================================================================
    if args.verbose:
        print(f"Scanning: {root_path}")
        print("Pass 1: Grouping files by name and size...")
    
    candidates = scan_directory(root_path, verbose=args.verbose)
    
    if not candidates:
        print("No potential duplicates found.")
        return 0
    
    if args.verbose:
        total_candidates = sum(len(v) for v in candidates.values())
        print(f"  Found {len(candidates)} groups with {total_candidates} potential duplicates")
    
    # =========================================================================
    # PASS 2: Verify with content hash
    # =========================================================================
    if args.verbose:
        print("Pass 2: Verifying duplicates with content hash...")
    
    duplicates = verify_duplicates(candidates, verbose=args.verbose)
    
    if not duplicates:
        print("No true duplicates found after hash verification.")
        return 0
    
    if args.verbose:
        total_dupes = sum(len(v) for v in duplicates.values())
        print(f"  Confirmed {len(duplicates)} duplicate groups with {total_dupes} files")
    
    # =========================================================================
    # Analysis and Reporting
    # =========================================================================
    if args.verbose:
        print("Calculating statistics...")
    stats = calculate_statistics(duplicates)
    
    if args.verbose:
        print("Analyzing filename patterns...")
    patterns = analyze_filename_patterns(duplicates)
    
    if args.verbose:
        print("Generating reports...")
    
    # Always generate JSON
    json_path = os.path.join(output_dir, 'duplicates_data.json')
    generate_json_report(duplicates, stats, patterns, json_path, root_path)
    print(f"  JSON report: {json_path}")
    
    # Generate text reports unless --json-only
    if not args.json_only:
        text_path = os.path.join(output_dir, 'duplicates_report.txt')
        generate_text_report(duplicates, stats, patterns, text_path, root_path)
        print(f"  Text report: {text_path}")
        
        summary_path = os.path.join(output_dir, 'statistics_summary.txt')
        generate_statistics_summary(stats, summary_path)
        print(f"  Statistics:  {summary_path}")
    
    # Print summary to console
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Duplicate groups found:    {stats['total_groups']}")
    print(f"Total duplicate files:     {stats['total_duplicate_files']}")
    print(f"Files that can be removed: {stats['total_files_removable']}")
    print(f"Recoverable space:         {format_size(stats['recoverable_size_bytes'])}")
    print("=" * 50)
    
    return 0


# This is the standard Python idiom for "run main() when script is executed"
# It prevents main() from running if this file is imported as a module
if __name__ == '__main__':
    exit(main())
