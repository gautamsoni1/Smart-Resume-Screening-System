"""
skill_extractor.py
-------------------
Detects which known technical skills appear in a given piece of text
(resume text OR job description text).

DESIGN NOTES:
- SKILL_DATABASE is the master list of recognized skills. It's a flat list of
  "canonical" display names. In a real production system this would likely
  live in a database/config file, but a Python list keeps this self-contained
  and easy to extend.
- SKILL_ALIASES maps common variant spellings/abbreviations to their
  canonical name so "ML" and "Machine Learning" both resolve to
  "Machine Learning", and "Postgres" resolves to "PostgreSQL", etc. This is
  "skill normalization".
- Matching uses regex word-boundaries (\\b) so that searching for "Java"
  doesn't accidentally match inside "JavaScript". Multi-word skills like
  "Machine Learning" and symbol-containing ones like "C++" are handled with
  carefully escaped patterns.
"""

import re
from typing import List, Set

from app.utils.text_preprocessing import clean_text

# ---------------------------------------------------------------------------
# 1. SKILL DATABASE -- canonical skill names we know how to detect.
# ---------------------------------------------------------------------------
SKILL_DATABASE: List[str] = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "SQL", "NoSQL", "FastAPI", "Django", "Flask", "Node.js", "React", "Angular",
    "Vue.js", "Machine Learning", "Deep Learning", "Natural Language Processing",
    "Computer Vision", "TensorFlow", "PyTorch", "Scikit-Learn", "Keras",
    "Pandas", "NumPy", "MongoDB", "PostgreSQL", "MySQL", "Redis", "AWS",
    "Azure", "GCP", "Docker", "Kubernetes", "Git", "CI/CD", "Linux",
    "REST API", "GraphQL", "HTML", "CSS", "Tableau", "Power BI", "Excel",
    "Spark", "Hadoop", "Airflow", "Selenium",
]

# ---------------------------------------------------------------------------
# 2. SKILL NORMALIZATION -- alias/abbreviation -> canonical name.
#    Keys MUST be lowercase. Values must exactly match an entry in
#    SKILL_DATABASE above.
# ---------------------------------------------------------------------------
SKILL_ALIASES = {
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "k8s": "Kubernetes",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "vue": "Vue.js",
    "sklearn": "Scikit-Learn",
    "scikit learn": "Scikit-Learn",
    "rest": "REST API",
    "restful api": "REST API",
    "power bi": "Power BI",
    "ci cd": "CI/CD",
}


def _build_skill_pattern(skill: str) -> re.Pattern:
    """
    Build a case-insensitive regex pattern for a single skill that:
    - Escapes regex special characters (important for "C++", "C#", "Node.js").
    - Uses word boundaries on the alphabetic ends only (so "C++" still matches
      even though \\b doesn't behave intuitively around '+').
    """
    escaped = re.escape(skill.lower())
    # For skills ending in symbols (++, #), don't force a trailing \b since
    # \b doesn't sit well next to non-word characters.
    pattern = r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])"
    return re.compile(pattern, re.IGNORECASE)


# Pre-compile patterns once at import time for performance.
_SKILL_PATTERNS = {skill: _build_skill_pattern(skill) for skill in SKILL_DATABASE}
_ALIAS_PATTERNS = {alias: _build_skill_pattern(alias) for alias in SKILL_ALIASES}


def extract_skills(text: str) -> List[str]:
    """
    Scan `text` and return the list of canonical skill names found in it,
    deduplicated and sorted alphabetically.

    Steps:
      1. Clean the text (lowercase, normalize whitespace) -- see
         text_preprocessing.clean_text for the rules applied.
      2. Run every canonical skill's regex against the cleaned text.
      3. Run every alias's regex against the cleaned text; if found, add the
         ALIAS'S canonical mapping instead of the alias itself
         (this is the "normalization" step).
      4. Return the deduplicated, sorted result as a List[str].
    """
    cleaned = clean_text(text)
    found: Set[str] = set()

    for skill, pattern in _SKILL_PATTERNS.items():
        if pattern.search(cleaned):
            found.add(skill)

    for alias, pattern in _ALIAS_PATTERNS.items():
        if pattern.search(cleaned):
            found.add(SKILL_ALIASES[alias])

    return sorted(found)