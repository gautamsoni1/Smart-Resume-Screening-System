"""
pdf_parser.py
-------------
Responsible for ONE thing: turning an uploaded PDF resume into plain text.

DESIGN NOTES:
- We use `pdfplumber` as the primary extraction engine because it generally
  handles multi-column resumes and tables better than PyPDF2.
- We wrap extraction in a try/except per-page so that ONE corrupted/garbled
  page doesn't crash extraction for the whole document -- we just skip that
  page and keep going.
- All errors are surfaced as a custom `PDFParsingError` so the route layer
  can catch a single, predictable exception type and turn it into a clean
  HTTP error response instead of a raw 500 traceback.
"""

import pdfplumber
from pathlib import Path


class PDFParsingError(Exception):
    """Raised when a PDF cannot be opened or contains no extractable text."""
    pass


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text content from a PDF file on disk.

    Args:
        file_path: Absolute or relative path to the saved PDF file.

    Returns:
        A single string containing the concatenated text of every page.

    Raises:
        PDFParsingError: if the file doesn't exist, isn't a valid PDF, or no
                          text could be extracted at all (e.g. a pure scanned
                          image PDF with no OCR layer).
    """
    path = Path(file_path)
    if not path.exists():
        raise PDFParsingError(f"File not found: {file_path}")

    extracted_pages = []

    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) == 0:
                raise PDFParsingError("PDF has no pages.")

            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text() or ""
                    extracted_pages.append(page_text)
                except Exception as page_err:
                    # Skip a broken page but keep processing the rest of the document.
                    extracted_pages.append("")
                    print(f"[pdf_parser] Warning: failed to extract page {page_number}: {page_err}")

    except PDFParsingError:
        raise
    except Exception as e:
        # Covers corrupted files, password-protected PDFs, invalid format, etc.
        raise PDFParsingError(f"Could not open/parse PDF '{path.name}': {e}")

    full_text = "\n".join(extracted_pages).strip()

    if not full_text:
        raise PDFParsingError(
            f"No extractable text found in '{path.name}'. "
            f"It may be a scanned/image-only PDF without OCR."
        )

    return full_text