import os
import re


def clean_filename(filename: str) -> str:
    """Clean filenames by removing common prefixes, tags, and fixing casing.

    This is the canonical cleaning function used across the project.
    """
    name, ext = os.path.splitext(filename)

    # Remove leading numeric prefix like '### ####' (may be followed by underscores/spaces)
    name = re.sub(r'^\d{3}\s*\d{4}[_\s-]*', '', name)

    # Replace underscores with spaces
    name = name.replace('_', ' ')

    # Remove region/language tags in parentheses or brackets
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
    name = re.sub(r"\s*\[[^\]]*\]\s*", ' ', name)

    # Clean up extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    # Fix common title casing heuristics
    words = name.split()
    cleaned = []
    for i, w in enumerate(words):
        if w.upper() in ['LEGO', 'USA', 'EU', 'UK', 'DS', 'III', 'II', 'I', 'NES', 'SNES', 'GBA', 'GBC', 'PSP', 'PS1', 'PS2', 'PS3', 'N64', 'GC']:
            cleaned.append(w.upper())
        elif i > 0 and w.lower() in ['the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on']:
            cleaned.append(w.lower())
        elif w.isupper() and len(w) > 3:
            cleaned.append(w.title())
        else:
            cleaned.append(w)

    name = ' '.join(cleaned)
    name = name.replace('  ', ' ').replace('111', 'III')

    return name + ext


def normalize_for_match(s: str) -> str:
    """Normalize strings for fuzzy matching: strip extension, remove tags, punctuation, and lowercase."""
    # Remove trailing extension
    s = re.sub(r"\.[a-z0-9]{1,5}$", "", s, flags=re.IGNORECASE)
    # Strip parenthesized/bracketed tags
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    # Replace non-alphanumeric with space
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s)
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s