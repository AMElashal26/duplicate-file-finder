#!/usr/bin/env python3
"""
Duplicate File Finder

A script that scans directories for duplicate files using a two-pass approach:
1. Fast filtering by filename + size
2. Accurate verification using content hash

Generates detailed reports with statistics and pattern analysis.
"""

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
# CORE SCANNER - Pass 1: Group by filename_size
# =============================================================================

def scan_directory(root_path: str, verbose: bool = False) -> Dict[str, List[str]]:
    """
    Recursively scan directory and group files by filename_size.
    
    Returns a dictionary where:
        - Key: "filename_size" (e.g., "photo.jpg_1024")
        - Value: List of full paths to files with that name and size
    """
    candidates = defaultdict(list)
    file_count = 0
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                file_size = os.path.getsize(filepath)
                key = f"{filename}_{file_size}"
                candidates[key].append(filepath)
                file_count += 1
                
                if verbose and file_count % 1000 == 0:
                    print(f"  Scanned {file_count} files...")
            except (OSError, PermissionError) as e:
                # Skip files we can't access
                if verbose:
                    print(f"Warning: Could not access {filepath}: {e}")
    
    if verbose:
        print(f"  Total files scanned: {file_count}")
    
    # Filter to only entries with potential duplicates (more than 1 file)
    return {k: v for k, v in candidates.items() if len(v) > 1}


# =============================================================================
# HASH VERIFICATION - Pass 2: Verify duplicates by content
# =============================================================================

def compute_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """
    Compute MD5 hash of a file, reading in chunks for memory efficiency.
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not hash {filepath}: {e}")
        return None


def verify_duplicates(candidates: Dict[str, List[str]], verbose: bool = False) -> Dict[str, List[str]]:
    """
    Verify candidate duplicates by computing content hashes.
    
    Returns a dictionary where:
        - Key: Content hash
        - Value: List of file paths with identical content
    """
    duplicates = defaultdict(list)
    total_groups = len(candidates)
    processed = 0
    
    for name_size_key, paths in candidates.items():
        processed += 1
        if verbose and processed % 100 == 0:
            print(f"  Hashing group {processed}/{total_groups}...")
        
        # Group files by their content hash
        hash_groups = defaultdict(list)
        for path in paths:
            file_hash = compute_file_hash(path)
            if file_hash:
                hash_groups[file_hash].append(path)
        
        # Only keep groups with actual duplicates
        for file_hash, hash_paths in hash_groups.items():
            if len(hash_paths) > 1:
                duplicates[file_hash].extend(hash_paths)
    
    return dict(duplicates)


# =============================================================================
# STATISTICS ENGINE
# =============================================================================

def calculate_statistics(duplicates: Dict[str, List[str]]) -> dict:
    """
    Calculate statistics about duplicate files.
    
    Returns statistics including:
        - Total duplicate groups
        - Total duplicate files
        - Space that could be recovered (keeping one of each)
        - Breakdown by file type
    """
    stats = {
        "total_groups": len(duplicates),
        "total_duplicate_files": 0,
        "total_files_removable": 0,  # All but one from each group
        "total_size_bytes": 0,
        "recoverable_size_bytes": 0,
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
        stats["total_files_removable"] += num_files - 1  # Keep one
        
        # Get file info from first file (they're all the same size)
        try:
            file_size = os.path.getsize(paths[0])
        except OSError:
            file_size = 0
        
        total_size = file_size * num_files
        recoverable = file_size * (num_files - 1)
        
        stats["total_size_bytes"] += total_size
        stats["recoverable_size_bytes"] += recoverable
        
        # Group by extension
        ext = os.path.splitext(paths[0])[1].lower() or "(no extension)"
        stats["by_extension"][ext]["groups"] += 1
        stats["by_extension"][ext]["total_files"] += num_files
        stats["by_extension"][ext]["removable_files"] += num_files - 1
        stats["by_extension"][ext]["total_size"] += total_size
        stats["by_extension"][ext]["recoverable_size"] += recoverable
    
    # Convert defaultdict to regular dict for JSON serialization
    stats["by_extension"] = dict(stats["by_extension"])
    
    return stats


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


# =============================================================================
# PATTERN ANALYSIS
# =============================================================================

def analyze_filename_patterns(duplicates: Dict[str, List[str]]) -> dict:
    """
    Analyze filename patterns to identify common duplication causes.
    
    Detects patterns like:
        - Copy suffixes: "file (1).txt", "file - Copy.txt"
        - Common prefixes/suffixes across duplicates
        - Numbered sequences
    """
    patterns = {
        "copy_patterns": [],      # Files with copy indicators
        "numbered_patterns": [],  # Files with numbers like (1), (2)
        "common_prefixes": {},    # Groups sharing prefixes
        "common_directories": defaultdict(int)  # Directories with most duplicates
    }
    
    # Regex patterns for common copy indicators
    copy_regex = re.compile(r'[\s\-_]*(copy|копия|\(\d+\)|\s\d+)[\s\-_]*', re.IGNORECASE)
    numbered_regex = re.compile(r'[\(\[\s](\d+)[\)\]\s]|_(\d+)(?=\.|$)')
    
    all_filenames = []
    
    for file_hash, paths in duplicates.items():
        for path in paths:
            filename = os.path.basename(path)
            dirname = os.path.dirname(path)
            
            all_filenames.append(filename)
            patterns["common_directories"][dirname] += 1
            
            # Check for copy patterns
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
    
    # Find common prefixes (files starting with same characters)
    prefix_groups = defaultdict(list)
    for filename in all_filenames:
        # Use first 5 characters as prefix (if long enough)
        if len(filename) >= 5:
            prefix = filename[:5].lower()
            prefix_groups[prefix].append(filename)
    
    # Only keep prefixes shared by multiple files
    patterns["common_prefixes"] = {
        k: v for k, v in prefix_groups.items() if len(v) > 2
    }
    
    # Sort directories by count and take top 10
    sorted_dirs = sorted(
        patterns["common_directories"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    patterns["common_directories"] = dict(sorted_dirs)
    
    # Limit copy/numbered patterns to avoid huge reports
    patterns["copy_patterns"] = patterns["copy_patterns"][:50]
    patterns["numbered_patterns"] = patterns["numbered_patterns"][:50]
    
    return patterns


# =============================================================================
# REPORT GENERATORS
# =============================================================================

def generate_text_report(
    duplicates: Dict[str, List[str]],
    stats: dict,
    patterns: dict,
    output_path: str,
    root_path: str
) -> None:
    """Generate human-readable text report."""
    
    with open(output_path, 'w', encoding='utf-8') as f:
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
        
        # Statistics by File Type
        f.write("-" * 40 + "\n")
        f.write("BY FILE TYPE\n")
        f.write("-" * 40 + "\n")
        f.write(f"{'Extension':<15} {'Groups':>8} {'Files':>8} {'Removable':>10} {'Recoverable':>12}\n")
        f.write("-" * 55 + "\n")
        
        # Sort by recoverable size
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
        
        # Detailed Duplicate Groups
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
    """Generate JSON report for programmatic use."""
    
    # Build detailed duplicate groups
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
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_statistics_summary(
    stats: dict,
    output_path: str
) -> None:
    """Generate a concise statistics summary file."""
    
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
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Find duplicate files in a directory tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/scan
  %(prog)s /path/to/scan --output ./reports
  %(prog)s . --verbose
        """
    )
    
    parser.add_argument(
        'directory',
        help='Directory to scan for duplicates'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='.',
        help='Output directory for reports (default: current directory)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print progress information'
    )
    
    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Only generate JSON report (skip text reports)'
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    root_path = os.path.abspath(args.directory)
    if not os.path.isdir(root_path):
        print(f"Error: '{args.directory}' is not a valid directory")
        return 1
    
    # Create output directory if needed
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the duplicate finder
    if args.verbose:
        print(f"Scanning: {root_path}")
    
    # Pass 1: Group by filename_size
    if args.verbose:
        print("Pass 1: Grouping files by name and size...")
    candidates = scan_directory(root_path, verbose=args.verbose)
    
    if not candidates:
        print("No potential duplicates found.")
        return 0
    
    if args.verbose:
        total_candidates = sum(len(v) for v in candidates.values())
        print(f"  Found {len(candidates)} groups with {total_candidates} potential duplicates")
    
    # Pass 2: Verify with hash
    if args.verbose:
        print("Pass 2: Verifying duplicates with content hash...")
    duplicates = verify_duplicates(candidates, verbose=args.verbose)
    
    if not duplicates:
        print("No true duplicates found after hash verification.")
        return 0
    
    if args.verbose:
        total_dupes = sum(len(v) for v in duplicates.values())
        print(f"  Confirmed {len(duplicates)} duplicate groups with {total_dupes} files")
    
    # Calculate statistics
    if args.verbose:
        print("Calculating statistics...")
    stats = calculate_statistics(duplicates)
    
    # Analyze patterns
    if args.verbose:
        print("Analyzing filename patterns...")
    patterns = analyze_filename_patterns(duplicates)
    
    # Generate reports
    if args.verbose:
        print("Generating reports...")
    
    json_path = os.path.join(output_dir, 'duplicates_data.json')
    generate_json_report(duplicates, stats, patterns, json_path, root_path)
    print(f"  JSON report: {json_path}")
    
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


if __name__ == '__main__':
    exit(main())

