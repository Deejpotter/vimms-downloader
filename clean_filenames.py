#!/usr/bin/env python3
"""
Nintendo DS ROM Filename Cleaner

This script cleans up Nintendo DS ROM filenames by:
- Removing numeric prefixes (e.g., "005 4426 ")
- Removing region/language tags (e.g., "(EU)", "(USA)", "(ML)")
- Replacing underscores with spaces
- Cleaning up extra whitespace
- Preserving file extensions
"""

import os
import re
from pathlib import Path


def clean_filename(filename):
    """
    Clean a single filename according to the rules.
    
    Args:
        filename: The original filename (including extension)
    
    Returns:
        The cleaned filename
    """
    # Split filename and extension
    name, ext = os.path.splitext(filename)

    # Step 1: Remove leading numeric prefix pattern like "### ####" which may be
    # followed by underscores, spaces or hyphens (examples: "005 4426__", "123 4567 - ")
    name = re.sub(r'^\d{3}\s*\d{4}[_\s-]*', '', name)

    # Step 2: Replace underscores with spaces (common formatting from dumps)
    name = name.replace('_', ' ')

    # Step 3: Remove region/language tags in parentheses or brackets
    # Matches patterns like (EU), (USA), (ML), (En,Fr,Es), [Europe], etc.
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
    name = re.sub(r"\s*\[[^\]]*\]\s*", ' ', name)

    # Also remove common explicit tags that might not be bracketed
    name = re.sub(r'\bNDSi\s+Enhanced\b', ' ', name, flags=re.IGNORECASE)
    
    # Step 4: Clean up multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Step 5: Trim whitespace
    name = name.strip()
    
    # Step 6: Fix common title casing issues
    # Convert all-caps words to title case (except small words and acronyms)
    words = name.split()
    cleaned_words = []
    
    for i, word in enumerate(words):
        # Keep known acronyms in caps
        if word.upper() in ['LEGO', 'USA', 'EU', 'UK', 'DS', 'III', 'II', 'I']:
            cleaned_words.append(word.upper())
        # Keep small words lowercase unless they're the first word
        elif i > 0 and word.lower() in ['the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on']:
            cleaned_words.append(word.lower())
        # If word is all caps and longer than 3 chars, convert to title case
        elif word.isupper() and len(word) > 3:
            cleaned_words.append(word.title())
        else:
            cleaned_words.append(word)
    
    name = ' '.join(cleaned_words)
    
    # Step 7: Fix common issues
    name = name.replace('  ', ' ')  # Double check for double spaces
    name = name.replace('111', 'III')  # Fix "111" to "III"
    
    # Return cleaned name with original extension
    return name + ext


def preview_changes(directory):
    """
    Preview all the changes that would be made.
    
    Args:
        directory: Path to the directory to scan
    
    Returns:
        List of tuples (old_name, new_name) for files that would change
    """
    changes = []
    
    for filename in os.listdir(directory):
        # Only process .nds and .sav files
        if not (filename.endswith('.nds') or filename.endswith('.sav') or filename.endswith('.NDS')):
            continue
        
        new_name = clean_filename(filename)
        
        # Only include if the name actually changes
        if new_name != filename:
            changes.append((filename, new_name))
    
    return changes


def rename_files(directory, changes, dry_run=True):
    """
    Rename files according to the changes list.
    
    Args:
        directory: Path to the directory containing files
        changes: List of tuples (old_name, new_name)
        dry_run: If True, don't actually rename files
    
    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    
    for old_name, new_name in changes:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        
        # Check if target file already exists
        if os.path.exists(new_path) and old_path != new_path:
            print(f"  ⚠️  SKIP: '{new_name}' already exists")
            error_count += 1
            continue
        
        if not dry_run:
            try:
                os.rename(old_path, new_path)
                print(f"  ✓ Renamed: '{old_name}' → '{new_name}'")
                success_count += 1
            except Exception as e:
                print(f"  ✗ ERROR: Could not rename '{old_name}': {e}")
                error_count += 1
        else:
            print(f"  • '{old_name}' → '{new_name}'")
            success_count += 1
    
    return success_count, error_count


def main():
    """Main function to run the filename cleaner."""
    # Get the directory where the script is located. Prefer a `ROMs` subfolder
    script_dir = Path(__file__).parent
    roms_dir = script_dir / 'ROMs'
    target_dir = roms_dir if roms_dir.exists() and roms_dir.is_dir() else script_dir

    print("=" * 70)
    print("Nintendo DS ROM Filename Cleaner")
    print("=" * 70)
    print(f"\nScanning directory: {target_dir}")
    print()
    
    # Preview changes
    changes = preview_changes(target_dir)
    
    if not changes:
        print("No files need cleaning. All filenames are already clean!")
        return
    
    print(f"Found {len(changes)} file(s) to clean:\n")
    
    # Show preview
    for old_name, new_name in changes:
        print(f"  '{old_name}'")
        print(f"    → '{new_name}'")
        print()
    
    # Ask for confirmation
    print("-" * 70)
    response = input(f"\nProceed with renaming {len(changes)} file(s)? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print("\nRenaming files...\n")
        success, errors = rename_files(target_dir, changes, dry_run=False)
        print(f"\n{'=' * 70}")
        print(f"Complete! Successfully renamed {success} file(s).")
        if errors > 0:
            print(f"⚠️  {errors} file(s) could not be renamed (see errors above).")
        print(f"{'=' * 70}")
    else:
        print("\nOperation cancelled. No files were renamed.")


if __name__ == "__main__":
    main()
