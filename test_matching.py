#!/usr/bin/env python3
"""Test filename matching to diagnose detection issues."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.filenames import clean_filename, normalize_for_match
import difflib

# Your actual filenames from the screenshot
your_files = [
    "2 Game Pack - My Amusement Park + Dr..nds",
    "2 Game Pack! - Monster Trucks Mayhem ..nds",
    "2-Pack - Pinkalicious - It's Party T..nds",
    "Ace Attorney Investigations - Miles Edgeworth.nds",
    "Advance Wars - Days of Ruin.nds",
]

# What Vimm's probably has (guessing based on pattern)
vimms_names = [
    "2-in-1 Game Pack: My Amusement Park + Dr. Panda's Hospital",
    "2-in-1 Game Pack!: Monster Trucks Mayhem + Dinosaurs",
    "2-Pack: Pinkalicious: It's Party Time! & Purr-fect Pet Shop",
    "Ace Attorney Investigations: Miles Edgeworth",
    "Advance Wars: Days of Ruin",
]

threshold = 0.65

print("Testing filename matching:\n")
for your_file, vimms_name in zip(your_files, vimms_names):
    cleaned_file = clean_filename(your_file)
    norm_file = normalize_for_match(cleaned_file)
    norm_vimms = normalize_for_match(vimms_name)
    
    # Check substring match
    substring_match = (norm_file in norm_vimms) or (norm_vimms in norm_file)
    
    # Check fuzzy match
    ratio = difflib.SequenceMatcher(None, norm_file, norm_vimms).ratio()
    fuzzy_match = ratio >= threshold
    
    matched = substring_match or fuzzy_match
    
    print(f"File: {your_file}")
    print(f"  Cleaned: {cleaned_file}")
    print(f"  Normalized: {norm_file}")
    print(f"Vimm's: {vimms_name}")
    print(f"  Normalized: {norm_vimms}")
    print(f"  Substring match: {substring_match}")
    print(f"  Fuzzy ratio: {ratio:.3f} (threshold: {threshold}) -> {fuzzy_match}")
    print(f"  MATCHED: {matched}")
    print()
