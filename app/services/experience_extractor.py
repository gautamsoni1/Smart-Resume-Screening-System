"""
experience_extractor.py
-------------------------
Extracts a candidate's total years of experience from free-text resume
content using regex patterns.

DESIGN NOTES:
- Resumes phrase experience in many inconsistent ways:
    "2 years experience", "3+ years", "Worked for 4 years",
    "5 yrs of experience", "Over 6 years in software development"
  Rather than one giant regex, we use a LIST of patterns, each targeting one
  common phrasing, tried in order against the cleaned text.
- When multiple experience mentions exist in a resume (e.g. "3 years at
  Company A" and "2 years at Company B" in different roles), we take the
  MAXIMUM number found rather than summing -- summing would double count
  overlapping employment history mentioned elsewhere (like a "5 years total"
  summary line), and a max is a safer, simpler heuristic for this scope.
"""

import re
from typing import Optional

# Patterns ordered from most specific to most general. Each captures a
# number (possibly with a '+') just before the word "year(s)"/"yr(s)".
EXPERIENCE_PATTERNS = [
    r"(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)\s+(?:of\s+)?experience",  # "2 years experience" / "3+ years of experience"
    r"experience\s+of\s+(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)",        # "experience of 4 years"
    r"worked\s+for\s+(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)",          # "worked for 4 years"
    r"over\s+(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)",                  # "over 6 years"
    r"(\d+(?:\.\d+)?)\+\s*(?:years|year|yrs|yr)",                          # "3+ years" (standalone, '+' required)
    r"(\d+(?:\.\d+)?)\s*(?:years|year|yrs|yr)\b",                          # generic fallback: "2 years"
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in EXPERIENCE_PATTERNS]


def extract_experience_years(text: str) -> Optional[float]:
    """
    Search `text` for every experience pattern and return the LARGEST number
    of years found across all matches, or None if nothing matched.
    """
    if not text:
        return None

    found_values = []

    for pattern in _COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            try:
                found_values.append(float(match.group(1)))
            except (ValueError, IndexError):
                continue

    if not found_values:
        return None

    return max(found_values)


def extract_experience_label(text: str) -> str:
    """
    Convenience wrapper used by the API layer: returns a clean display
    string like "2 Years" / "3.5 Years", or "Not specified" if no experience
    duration could be found anywhere in the resume.
    """
    years = extract_experience_years(text)

    if years is None:
        return "Not specified"

    # Format whole numbers without a trailing ".0" (e.g. "2 Years" not "2.0 Years").
    if years == int(years):
        years_str = str(int(years))
    else:
        years_str = str(years)

    label = "Year" if years == 1 else "Years"
    return f"{years_str} {label}"