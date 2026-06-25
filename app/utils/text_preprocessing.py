"""
text_preprocessing.py
----------------------
Shared low-level text cleaning utilities used by both the skill extractor
and the TF-IDF matcher.
"""

import re


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\+\#\.\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list:
    return clean_text(text).split()