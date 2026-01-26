#!/usr/bin/env python3
"""Test script to verify game name matching works correctly."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.filenames import clean_filename, normalize_for_match

# Test cases: (remote_game_name, local_filename, should_match)
test_cases = [
    ("Ace Attorney Investigations: Miles Edgeworth", "005 4426__Ace_Attorney_Investigations_Miles_Edgeworth_(USA).nds", True),
    ("Advance Wars: Days of Ruin", "0123 4567__Advance_Wars_Days_of_Ruin_(USA).nds", True),
    ("Super Mario 64 DS", "Super Mario 64 DS.nds", True),
    ("The Legend of Zelda: Phantom Hourglass", "Legend of Zelda, The - Phantom Hourglass (USA).nds", True),
    ("Pokemon Diamond", "Pokemon - Diamond Version (USA).nds", True),
]

print("Testing game name matching logic:\n")
print("=" * 80)

for remote_name, local_file, expected_match in test_cases:
    # Clean and normalize both
    remote_cleaned = clean_filename(remote_name)
    remote_normalized = normalize_for_match(remote_cleaned)
    
    local_cleaned = clean_filename(local_file)
    local_normalized = normalize_for_match(local_cleaned)
    
    # Test substring matching (first check in find_all_matching_files)
    substring_match = remote_normalized in local_normalized or local_normalized in remote_normalized
    
    # Test fuzzy ratio (second check)
    import difflib
    ratio = difflib.SequenceMatcher(None, remote_normalized, local_normalized).ratio()
    fuzzy_match = ratio >= 0.75
    
    overall_match = substring_match or fuzzy_match
    
    status = "✓" if overall_match == expected_match else "✗"
    
    print(f"\n{status} Remote: '{remote_name}'")
    print(f"  Local:  '{local_file}'")
    print(f"  Remote cleaned:    '{remote_cleaned}'")
    print(f"  Remote normalized: '{remote_normalized}'")
    print(f"  Local cleaned:     '{local_cleaned}'")
    print(f"  Local normalized:  '{local_normalized}'")
    print(f"  Substring match: {substring_match}")
    print(f"  Fuzzy ratio: {ratio:.3f} (match: {fuzzy_match})")
    print(f"  Overall: {overall_match} (expected: {expected_match})")
    print("-" * 80)

print("\n" + "=" * 80)
print("Test complete!")
