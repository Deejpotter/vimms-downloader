"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cleanFilename = cleanFilename;
exports.normalizeForMatch = normalizeForMatch;
function cleanFilename(filename) {
    const parts = filename.split(/(\.[^.]+)$/);
    let name = parts[0];
    const ext = parts[1] || "";
    // Remove leading numeric prefix like '### ####' (may be followed by underscores/spaces)
    name = name.replace(/^\d{3}\s*\d{4}[_\s-]*/, "");
    // Replace underscores with spaces
    name = name.replace(/_/g, " ");
    // Remove region/language tags in parentheses or brackets
    name = name.replace(/\s*\([^)]*\)\s*/g, " ");
    name = name.replace(/\s*\[[^\]]*\]\s*/g, " ");
    // Clean up extra whitespace
    name = name.replace(/\s+/g, " ").trim();
    const words = name.split(" ");
    const cleaned = [];
    const UPPER = [
        "LEGO",
        "USA",
        "EU",
        "UK",
        "DS",
        "III",
        "II",
        "I",
        "NES",
        "SNES",
        "GBA",
        "GBC",
        "PSP",
        "PS1",
        "PS2",
        "PS3",
        "N64",
        "GC",
    ];
    const SMALL_WORDS = ["the", "a", "an", "and", "or", "of", "to", "in", "on"];
    words.forEach((w, i) => {
        if (UPPER.includes(w.toUpperCase()))
            cleaned.push(w.toUpperCase());
        else if (i > 0 && SMALL_WORDS.includes(w.toLowerCase()))
            cleaned.push(w.toLowerCase());
        else if (w === w.toUpperCase() && w.length > 3)
            cleaned.push(w);
        else
            cleaned.push(w);
    });
    name = cleaned.join(" ");
    name = name.replace(/  /g, " ").replace(/111/g, "III");
    return name + ext;
}
function normalizeForMatch(s) {
    // Remove trailing extension
    s = s.replace(/\.[a-z0-9]{1,5}$/i, "");
    // Strip parenthesized/bracketed tags
    s = s.replace(/\([^)]*\)/g, "");
    s = s.replace(/\[[^\]]*\]/g, "");
    // Replace non-alphanumeric with space
    s = s.replace(/[^A-Za-z0-9 ]+/g, " ");
    s = s.toLowerCase().trim();
    s = s.replace(/\s+/g, " ");
    return s;
}
